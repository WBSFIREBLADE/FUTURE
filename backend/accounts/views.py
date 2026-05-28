import logging

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from .serializers import UserSearilizers, LogoutSerializer
from rest_framework_simplejwt.tokens import RefreshToken

logger = logging.getLogger(__name__)


class RegisterView(APIView):
    def post(self, request):
        logger.info("Register request received", extra={"email": request.data.get("email"), "username": request.data.get("username")})
        serializer = UserSearilizers(data=request.data)
        
        if serializer.is_valid():
            serializer.save()
            logger.info("User registered successfully", extra={"username": request.data.get("username")})
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        
        logger.warning("Register request failed", extra={"errors": serializer.errors})
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    


class LogoutAPIView(APIView):
    def post(self, request):
        logger.info("Logout request received")
        serializer = LogoutSerializer(data=request.data)
        
        if serializer.is_valid():
            try:
                refresh_token = serializer.validated_data["refresh"]
                token = RefreshToken(refresh_token)
                token.blacklist()
                logger.info("Logout successful")
                return Response({"message": "Logout successful"}, status=status.HTTP_205_RESET_CONTENT)
            
            except Exception as e:
                logger.exception("Logout failed due to invalid token")
                return Response({"error": "Invalid token"}, status=status.HTTP_400_BAD_REQUEST)

        logger.warning("Logout validation failed", extra={"errors": serializer.errors})
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class FrontendLogView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        level = str(request.data.get("level", "INFO")).upper()
        message = request.data.get("message", "<no message>")
        context = request.data.get("context", {})

        logger_message = f"FRONTEND log - {message} | context={context}"

        if level == "ERROR":
            logger.error(logger_message)
        elif level == "WARNING":
            logger.warning(logger_message)
        else:
            logger.info(logger_message)

        return Response({"success": True}, status=status.HTTP_200_OK)
