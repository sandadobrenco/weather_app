import grpc
from server.config import cfg
from log.config import get_logger

log = get_logger("auth_interceptor")

class AuthInterceptor(grpc.aio.ServerInterceptor):
    async def intercept_service(self, continuation, handler_call_details):
        base_handler = await continuation(handler_call_details)

        if not cfg.service_api_key:  
            return base_handler

        metadata = dict(handler_call_details.invocation_metadata or [])
        provided_key = metadata.get("x-api-key") or metadata.get(b"x-api-key")

        if provided_key == cfg.service_api_key:
            return base_handler
        
        log.warning("auth.unauthenticated")
            
        async def deny(request, context):
            await context.abort(grpc.StatusCode.UNAUTHENTICATED, "Invalid or missing x-api-key")
        
        aio_ctor = getattr(getattr(grpc, "aio", object), "unary_unary_rpc_method_handler", None)
        if aio_ctor and hasattr(base_handler, "unary_unary"):
            return aio_ctor(deny)
        
        class _UnaryUnaryDenyHandler:
            request_streaming = False
            response_streaming = False
            
            def __init__(self, base):
                self.request_deserializer = getattr(base, "request_deserializer", None)
                self.response_serializer = getattr(base, "response_serializer", None)
            
            async def unary_unary(self, request, context):
                return await deny(request, context)
        
        return _UnaryUnaryDenyHandler(base_handler)