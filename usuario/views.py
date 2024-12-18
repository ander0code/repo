from adrf.viewsets import ViewSet
from spanlp.palabrota import Palabrota
from rest_framework import serializers
from django.contrib.auth.models import User
from django.utils.timezone import now
from django.utils import timezone 
from django.db.models import Count
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from rest_framework.response import Response
from rest_framework import status
from .serializers import LoginSerializer, ProjectSerializerCreate,CustomUserSerializer, ProjectSerializerAll,SolicitudSerializer,ProjectSerializerID,ProjectUpdateSerializer,CollaboratorSerializer,ProjectSerializer, NotificationSerializer,ProfileSerializer, NotificationSerializerMS, FormSerializer, UserAchievementsSerializer, AchievementsSerializer
from rest_framework.decorators import action
from rest_framework_simplejwt.tokens import RefreshToken
from django.core.mail import send_mail
from django.shortcuts import get_object_or_404
from usuario.models import Users,Projects,Solicitudes,Collaborations, Notifications, Forms, Achievements, UserAchievements
from rest_framework.permissions import AllowAny ,IsAuthenticated
from django.db import transaction
from spanlp.palabrota import Palabrota
from spanlp.domain.strategies import Preprocessing, TextToLower, RemoveAccents
import random
import logging

logger = logging.getLogger(__name__)

from asgiref.sync import sync_to_async

class LoginViewSet(ViewSet): #(User Management)
    
    @swagger_auto_schema(
        operation_summary="Logearse como usuario y obtener tokens JWT",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['email', 'password'],
            properties={
                'email': openapi.Schema(type=openapi.TYPE_STRING, description='User email'),
                'password': openapi.Schema(type=openapi.TYPE_STRING, description='User password'),
            },
        ),
        responses={
            200: openapi.Response('Successful login', 
                                  openapi.Schema(
                                      type=openapi.TYPE_OBJECT,
                                      properties={
                                          'access': openapi.Schema(type=openapi.TYPE_STRING, description='Access token for authentication'),
                                          'refresh': openapi.Schema(type=openapi.TYPE_STRING, description='Refresh token for obtaining new access tokens'),
                                          'email': openapi.Schema(type=openapi.TYPE_STRING, description='Email of the logged-in user'),
                                      }
                                  )),
            400: openapi.Response('Invalid credentials', 
                                  openapi.Schema(
                                      type=openapi.TYPE_OBJECT,
                                      properties={
                                          'error': openapi.Schema(type=openapi.TYPE_STRING, description='Error message'),
                                      }
                                  )),
        },
        tags=["User Management"]
    )
    @action(detail=False, methods=['POST'],url_path='Login', permission_classes=[AllowAny])
    async def Login(self, request):
        try:
            serializer = LoginSerializer(data=request.data)
            if await sync_to_async(serializer.is_valid)(raise_exception=False):
                return Response(serializer.validated_data, status=status.HTTP_200_OK)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
    @swagger_auto_schema(
        operation_summary="Registrarse y logearse como usuario y obtener tokens JWT",
        operation_description="Register a new user and return JWT tokens",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['email', 'password', 'university', 'career', 'cycle', 'biography', 'photo', 'achievements', 'first_name', 'last_name'],
            properties={
                'email': openapi.Schema(type=openapi.TYPE_STRING, description='Email of the user'),
                'password': openapi.Schema(type=openapi.TYPE_STRING, description='Password of the user'),
                'university': openapi.Schema(type=openapi.TYPE_STRING, description='University of the user'),
                'career': openapi.Schema(type=openapi.TYPE_STRING, description='Career of the user'),
                'cycle': openapi.Schema(type=openapi.TYPE_STRING, description='Cycle of the user'),
                'biography': openapi.Schema(type=openapi.TYPE_STRING, description='Biography of the user'),
                'photo': openapi.Schema(type=openapi.TYPE_STRING, description='Photo URL of the user'),
                'achievements': openapi.Schema(type=openapi.TYPE_STRING, description='Achievements of the user'),
                'first_name': openapi.Schema(type=openapi.TYPE_STRING, description='First name of the user'),
                'last_name': openapi.Schema(type=openapi.TYPE_STRING, description='Last name of the user'),
                'interests': openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Items(type=openapi.TYPE_STRING, maxLength=500),
                    description='List of interests of the user (optional)'
                ),
            },
        ),
        responses={
            status.HTTP_201_CREATED: openapi.Response(
                'User registered successfully and JWT tokens returned',
                openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'refresh': openapi.Schema(type=openapi.TYPE_STRING, description='Refresh token'),
                        'access': openapi.Schema(type=openapi.TYPE_STRING, description='Access token'),
                        'user': openapi.Schema(type=openapi.TYPE_OBJECT, description='User data', properties={
                            'authuser': openapi.Schema(type=openapi.TYPE_INTEGER, description='ID of the associated auth user'),
                            'university': openapi.Schema(type=openapi.TYPE_STRING, description='University of the user'),
                            'career': openapi.Schema(type=openapi.TYPE_STRING, description='Career of the user'),
                            'cycle': openapi.Schema(type=openapi.TYPE_STRING, description='Cycle of the user'),
                            'interests': openapi.Schema(
                                type=openapi.TYPE_ARRAY,
                                items=openapi.Items(type=openapi.TYPE_STRING, maxLength=500),
                                description='List of interests of the user'
                            ),
                            'biography': openapi.Schema(type=openapi.TYPE_STRING, description='Biography of the user'),
                            'photo': openapi.Schema(type=openapi.TYPE_STRING, description='Photo URL of the user'),
                            'achievements': openapi.Schema(type=openapi.TYPE_STRING, description='Achievements of the user'),
                            'created_at': openapi.Schema(type=openapi.TYPE_STRING, description='Creation date of the user record', format='date'),
                        }),
                    },
                ),
            ),
            status.HTTP_400_BAD_REQUEST: openapi.Response('Invalid input data'),
        },
        tags=["User Management"]
    )
    @action(detail=False, methods=['POST'], url_path='Register', permission_classes=[AllowAny])
    async def register(self, request):
        email = request.data.get("email")
        password = request.data.get("password")
        first_name = request.data.get("first_name")
        last_name = request.data.get("last_name")

        logger.info("Inicio del registro de usuario.")  

        if not email or not password or not first_name or not last_name:
            logger.warning("Faltan campos obligatorios en la solicitud.")
            return Response({"error": "Email, password, first_name, and last_name are required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            def create_user_transaction():
                with transaction.atomic():

                    logger.info("Creando usuario en auth_user.")
                    user = User.objects.create_user(
                        username=email,
                        email=email,
                        password=password,
                        first_name=first_name,
                        last_name=last_name
                    )
                    logger.info(f"Usuario creado en auth_user con ID: {user.pk}")

                    logger.info("Creando registro relacionado en la tabla users.")
                    user_profile = Users.objects.create(
                        authuser=user,
                        university=request.data.get("university", ""),
                        career=request.data.get("career", ""),
                        cycle=request.data.get("cycle", ""),
                        biography=request.data.get("biography", ""),
                        photo=request.data.get("photo", ""),
                        achievements=request.data.get("achievements", ""),
                        interests=request.data.get("interests", []),
                        created_at=now(),
                    )
                    logger.info(f"Registro en la tabla users creado para authuser ID: {user.pk}")

                    return user, user_profile

            user, user_profile = await sync_to_async(create_user_transaction)()

            logger.info(f"Generando tokens JWT para el usuario ID: {user.pk}")
            refresh = RefreshToken.for_user(user)

            logger.info(f"Registro completado exitosamente para el usuario ID: {user.pk}")
            return Response({
                "refresh": str(refresh),
                "access": str(refresh.access_token),
                "user": {
                    "authuser_id": user.pk,
                    "email": user.email,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "university": user_profile.university,
                    "career": user_profile.career,
                    "cycle": user_profile.cycle,
                },
            }, status=status.HTTP_201_CREATED)

        except Exception as e:
            logger.error(f"Error inesperado durante el registro: {str(e)}")
            return Response({"error": "An unexpected error occurred."}, status=status.HTTP_400_BAD_REQUEST)

    
    @swagger_auto_schema(
        operation_summary="recuperar y crear la contraseña nueva del usuario",
            operation_description="Nos permite recuperar la contraseña del usuario y crear una nueva contraseña mediante el email registrado",
            request_body=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                required=['email'],
                properties={
                    'email': openapi.Schema(type=openapi.TYPE_STRING, description='User email to send the reset code'),
                },
            ),
            responses={
                200: openapi.Response('Password reset code sent', 
                                    openapi.Schema(type=openapi.TYPE_OBJECT, properties={
                                        'message': openapi.Schema(type=openapi.TYPE_STRING, description='Success message'),
                                    })),
                400: openapi.Response('Invalid email', 
                                    openapi.Schema(type=openapi.TYPE_OBJECT, properties={
                                        'error': openapi.Schema(type=openapi.TYPE_STRING, description='Error message'),
                                    })),
            },
            tags=["User Management"]
        )
    @action(detail=False, methods=['POST'], url_path='request-password-reset', permission_classes=[AllowAny])
    async def request_password_reset(self, request):
        email = request.data.get("email")

        if not email:
            return Response({"error": "Email is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:

            user = await sync_to_async(User.objects.get)(email=email)


            reset_code = random.randint(100000, 999999)

            user_profile = await sync_to_async(Users.objects.get)(authuser=user)
            user_profile.reset_code = reset_code  
            user_profile.reset_code_created_at = timezone.now()
            await sync_to_async(user_profile.save)()

            send_mail(
                'Password Reset Code',
                f'Your password reset code is: {reset_code}',
                'noreply@yourdomain.com',  
                [email],
                fail_silently=False,
            )

            return Response({"message": "Password reset code sent"}, status=status.HTTP_200_OK)

        except User.DoesNotExist:
            return Response({"error": "Invalid email"}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
    @swagger_auto_schema(
        operation_description="Reset user password using a reset code",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['email', 'reset_code', 'new_password'],
            properties={
                'email': openapi.Schema(type=openapi.TYPE_STRING, description='User email'),
                'reset_code': openapi.Schema(type=openapi.TYPE_INTEGER, description='Reset code sent to the user'),
                'new_password': openapi.Schema(type=openapi.TYPE_STRING, description='New password for the user'),
            },
        ),
        responses={
            200: openapi.Response('Password successfully reset', 
                                  openapi.Schema(type=openapi.TYPE_OBJECT, properties={
                                      'message': openapi.Schema(type=openapi.TYPE_STRING, description='Success message'),
                                  })),
            400: openapi.Response('Invalid reset code or email', 
                                  openapi.Schema(type=openapi.TYPE_OBJECT, properties={
                                      'error': openapi.Schema(type=openapi.TYPE_STRING, description='Error message'),
                                  })),
        },
        tags=["User Management"]
    )
    @action(detail=False, methods=['POST'], url_path='reset_password', permission_classes=[AllowAny])
    async def reset_password(self, request):
        email = request.data.get("email")
        reset_code = request.data.get("reset_code")
        new_password = request.data.get("new_password")
        
        try:

            user = await sync_to_async(User.objects.get)(email=email)
            
            user_profile = await sync_to_async(Users.objects.get)(authuser=user)

            if user_profile.reset_code == reset_code:
  
                user.set_password(new_password)
                await sync_to_async(user.save)() 
                
                user_profile.reset_code = None
                await sync_to_async(user_profile.save)()  
                
                return Response({"message": "Password successfully reset"}, status=status.HTTP_200_OK)
            else:
                return Response({"error": "Invalid reset code"}, status=status.HTTP_400_BAD_REQUEST)
        except User.DoesNotExist:
            return Response({"error": "Invalid email"}, status=status.HTTP_400_BAD_REQUEST)
        except Users.DoesNotExist:
            return Response({"error": "User profile not found"}, status=status.HTTP_400_BAD_REQUEST)

    @swagger_auto_schema(
        operation_description="Delete a user and their associated auth_user entry by ID",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['id'],
            properties={
                'id': openapi.Schema(type=openapi.TYPE_INTEGER, description='ID of the user to view'),
            },
        ),
        responses={
            status.HTTP_204_NO_CONTENT: openapi.Response('User and auth_user deleted successfully'),
            status.HTTP_404_NOT_FOUND: openapi.Response('User not found'),
        },
        tags=["User Management"]
    )
    @action(detail=False, methods=['DELETE'], url_path='delete-user', permission_classes=[IsAuthenticated])
    async def delete_user(self, request):

        user_id = request.data.get('id')
        try:

            user_profile = await sync_to_async(Users.objects.get)(pk=user_id)
            
            auth_user = user_profile.authuser  

        except Users.DoesNotExist:
            return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)

        await sync_to_async(user_profile.delete)()

        await sync_to_async(auth_user.delete)()

        return Response(status=status.HTTP_204_NO_CONTENT)
 
class PerfilViewSet(ViewSet): #(Profile Management)
    
    @swagger_auto_schema(
        method='post',
        operation_summary="Traer los datos del usuario",
        operation_description="trae los datos del usuario logeado",
        responses={
            200: openapi.Response(
                description="Successful response with user profile data.",
                schema=ProfileSerializer()
            ),
            404: openapi.Response(description="User profile not found.")
        },
        tags = ["Profile Management"]
    )
    @action(detail=False, methods=['POST'], url_path='profile', permission_classes=[IsAuthenticated])
    async def profile_data(self, request):
        user_id = request.user.id

        try:
            user_profile = await sync_to_async(Users.objects.get)(authuser_id=user_id)
            auth_user =  await sync_to_async(User.objects.get)(id=user_id)

            profile_data = {
                "university": user_profile.university,
                "career": user_profile.career,
                "cycle": user_profile.cycle,
                "biography": user_profile.biography,
                "interests": user_profile.interests,
                "photo": user_profile.photo,
                "achievements": user_profile.achievements,
                "created_at": user_profile.created_at,
                # Datos de authuser
                "email": auth_user.email,
                "first_name": auth_user.first_name,
                "last_name": auth_user.last_name,
                "date_joined": auth_user.date_joined,
            }

            serializer = ProfileSerializer(profile_data)
            return Response(serializer.data, status=200)

        except Users.DoesNotExist:
            return Response({"error": "User profile not found"}, status=404)

    @swagger_auto_schema(
        method='post',
        operation_summary="Traer los datos del usuario por id",
        operation_description="trae los datos del usuario por id",
        request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        required=['user_id'],
        properties={
                'user_id': openapi.Schema(type=openapi.TYPE_INTEGER, description='ID of the user'),
            },
        ),
        responses={
            200: openapi.Response(
                description='Profile data retrieved successfully',
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'university': openapi.Schema(type=openapi.TYPE_STRING, description='University of the user'),
                        'career': openapi.Schema(type=openapi.TYPE_STRING, description='Career of the user'),
                        'cycle': openapi.Schema(type=openapi.TYPE_STRING, description='Current cycle of the user'),
                        'biography': openapi.Schema(type=openapi.TYPE_STRING, description='Biography of the user'),
                        'interests': openapi.Schema(type=openapi.TYPE_STRING, description='Interests of the user'),
                        'photo': openapi.Schema(type=openapi.TYPE_STRING, format='uri', description='Profile photo URL'),
                        'achievements': openapi.Schema(type=openapi.TYPE_STRING, description='Achievements of the user'),
                        'created_at': openapi.Schema(type=openapi.TYPE_STRING, format='date-time', description='Profile creation date'),
                        'email': openapi.Schema(type=openapi.TYPE_STRING, description='Email of the user'),
                        'first_name': openapi.Schema(type=openapi.TYPE_STRING, description='First name of the user'),
                        'last_name': openapi.Schema(type=openapi.TYPE_STRING, description='Last name of the user'),
                        'date_joined': openapi.Schema(type=openapi.TYPE_STRING, format='date-time', description='Date when the user joined'),
                    }
                )
            ),
            404: openapi.Response(description='User profile not found'),
            400: openapi.Response(description='Invalid request'),
        },
        
        tags = ["Profile Management"]
    )
    @action(detail=False, methods=['POST'], url_path='profile_id', permission_classes=[IsAuthenticated])
    async def profile_data_id(self, request):
        
        user_id = request.data.get('user_id')

        try:
            user_profile = await sync_to_async(Users.objects.get)(authuser_id=user_id)
            auth_user = await sync_to_async(User.objects.get)(id=user_id)

            profile_data = {
                "university": user_profile.university,
                "career": user_profile.career,
                "cycle": user_profile.cycle,
                "biography": user_profile.biography,
                "interests": user_profile.interests,
                "photo": user_profile.photo,
                "achievements": user_profile.achievements,
                "created_at": user_profile.created_at,
                # Datos de authuser
                "email": auth_user.email,
                "first_name": auth_user.first_name,
                "last_name": auth_user.last_name,
                "date_joined": auth_user.date_joined,
            }

            serializer = ProfileSerializer(profile_data)
            return Response(serializer.data, status=200)

        except Users.DoesNotExist:
            return Response({"error": "User profile not found"}, status=404)


    @swagger_auto_schema(
        operation_description="Update user profile by ID. Accepts various fields such as university, career, cycle, biography, interests, photo, achievements, and created_at.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['id'],
            properties={
                'id': openapi.Schema(type=openapi.TYPE_INTEGER, description='ID of the user to view'),
                'university': openapi.Schema(type=openapi.TYPE_STRING, description='University of the user'),
                'career': openapi.Schema(type=openapi.TYPE_STRING, description='Career of the user'),
                'cycle': openapi.Schema(type=openapi.TYPE_STRING, description='Cycle of the user'),
                'biography': openapi.Schema(type=openapi.TYPE_STRING, description='Biography of the user'),
                'interests': openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Items(type=openapi.TYPE_STRING, maxLength=500),
                    description='List of user interests (maximum 500 characters each)'
                ),
                'photo': openapi.Schema(type=openapi.TYPE_STRING, description='Photo URL of the user'),
                'achievements': openapi.Schema(type=openapi.TYPE_STRING, description='Achievements of the user'),
            },
        ),
        responses={
            status.HTTP_200_OK: openapi.Response(
                'User profile updated successfully',
                openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'university': openapi.Schema(type=openapi.TYPE_STRING, description='University of the user'),
                        'career': openapi.Schema(type=openapi.TYPE_STRING, description='Career of the user'),
                        'cycle': openapi.Schema(type=openapi.TYPE_STRING, description='Cycle of the user'),
                        'biography': openapi.Schema(type=openapi.TYPE_STRING, description='Biography of the user'),
                        'interests': openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            items=openapi.Items(type=openapi.TYPE_STRING, maxLength=500),
                            description='List of user interests'
                        ),
                        'photo': openapi.Schema(type=openapi.TYPE_STRING, description='Photo URL of the user'),
                        'achievements': openapi.Schema(type=openapi.TYPE_STRING, description='Achievements of the user'),
                        'created_at': openapi.Schema(type=openapi.TYPE_STRING, description='Profile creation date, format YYYY-MM-DD')
                    }
                )
            ),
            status.HTTP_404_NOT_FOUND: openapi.Response('User not found'),
            status.HTTP_400_BAD_REQUEST: openapi.Response('Invalid input data'),
        },
        tags=["Profile Management"]
    )
    @action(detail=False, methods=['PUT'], url_path='update-profile',permission_classes=[IsAuthenticated])
    async def update_user_profile(self, request):

        user_id = request.data.get('id')
        try:
            user_profile = await sync_to_async(Users.objects.get)(pk=user_id)
        except Users.DoesNotExist:
            return Response({"error": "User profile not found"}, status=status.HTTP_404_NOT_FOUND)

        serializer = CustomUserSerializer(user_profile, data=request.data, partial=True)

        if await sync_to_async(serializer.is_valid)():
            await sync_to_async(serializer.save)()  
            return Response(serializer.data, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class ProjectViewSet(ViewSet): #(Projects Management)
     
    @swagger_auto_schema(
        operation_description="Create a new project",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['name', 'description', 'project_type', 'priority'],
            properties={
                'name': openapi.Schema(type=openapi.TYPE_STRING, description='Name of the project'),
                'description': openapi.Schema(type=openapi.TYPE_STRING, description='Description of the project'),
                'end_date': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATETIME, description='End date of the project'),
                'status': openapi.Schema(type=openapi.TYPE_STRING, description='Current status of the project'),
                'project_type': openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Items(type=openapi.TYPE_STRING),
                    description="List of project types"
                ),
                'priority': openapi.Schema(type=openapi.TYPE_STRING, description='Priority level of the project'),
                'detailed_description': openapi.Schema(type=openapi.TYPE_STRING, description='Detailed description of the project'),
                'objectives': openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Items(type=openapi.TYPE_STRING),
                    description='List of objectives for the project'
                ),
                'necessary_requirements': openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Items(type=openapi.TYPE_STRING),
                    description='List of necessary requirements for the project'
                ),
                'progress': openapi.Schema(type=openapi.TYPE_INTEGER, description='Progress percentage of the project'),
                'accepting_applications': openapi.Schema(type=openapi.TYPE_BOOLEAN, description='Indicates if the project is accepting applications'),
                'type_aplyuni': openapi.Schema(type=openapi.TYPE_STRING, description='Specifies application type (e.g., university-restricted or open to all)'),
            },
        ),
        responses={
            status.HTTP_201_CREATED: openapi.Response('Project created successfully'),
            status.HTTP_400_BAD_REQUEST: openapi.Response('Invalid input data'),
        },
        tags=["Projects Management"]
    )
    @action(detail=False, methods=['POST'], url_path='create_project', permission_classes=[IsAuthenticated])
    async def create_project(self, request):
        responsible_user_id = request.user.id

        # Configuración del detector de malas palabras
        palabrota_detector = Palabrota()
        preprocess_strategies = [TextToLower(), RemoveAccents()]

        # Preprocesar texto y validar malas palabras
        def preprocess_and_validate(value):
            if isinstance(value, str):
                # Preprocesar el texto
                preprocessed_value = Preprocessing(data=value, clean_strategies=preprocess_strategies).clean()
                # Verificar si contiene malas palabras
                return palabrota_detector.contains_palabrota(preprocessed_value)
            elif isinstance(value, list):
                # Validar cada elemento de la lista
                return any(preprocess_and_validate(item) for item in value)
            return False

        try:
            custom_user = await sync_to_async(Users.objects.get)(authuser=responsible_user_id)
        except Users.DoesNotExist:
            return Response({"error": "User profile not found"}, status=status.HTTP_404_NOT_FOUND)

        project_data = request.data
        project_data['start_date'] = timezone.now().strftime('%Y-%m-%d')
        project_data['name_uniuser'] = custom_user.university if custom_user.university else ""
        project_data['responsible'] = responsible_user_id

        # Validar campos para detectar contenido inapropiado
        for field in ['name', 'description', 'detailed_description', 'objectives', 'necessary_requirements']:
            if field in project_data and preprocess_and_validate(project_data[field]):
                return Response(
                    {"error": "Esta acción no cumple con las políticas de contenido aceptable. Por favor, revise los datos ingresados y vuelva a intentarlo."},
                    status=status.HTTP_400_BAD_REQUEST
                )

        # Validar y guardar el proyecto
        project_serializer = ProjectSerializerCreate(data=project_data)
        if await sync_to_async(project_serializer.is_valid)():
            await sync_to_async(project_serializer.save)()
            return Response({"status": "Project created successfully"}, status=status.HTTP_201_CREATED)

        return Response(project_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @swagger_auto_schema(
        operation_description="Actualizar un proyecto específico pasando el ID y los datos del proyecto en el cuerpo de la solicitud",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'project_id': openapi.Schema(type=openapi.TYPE_INTEGER, description='ID del proyecto'),
                'name': openapi.Schema(type=openapi.TYPE_STRING, description='Nombre del proyecto'),
                'description': openapi.Schema(type=openapi.TYPE_STRING, description='Descripción del proyecto'),
                'start_date': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATE, description='Fecha de inicio del proyecto'),
                'end_date': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATE, description='Fecha de finalización del proyecto'),
                'status': openapi.Schema(type=openapi.TYPE_STRING, description='Estado actual del proyecto'),
                'project_type': openapi.Schema(type=openapi.TYPE_STRING, description='Tipo de proyecto'),
                'priority': openapi.Schema(type=openapi.TYPE_STRING, description='Nivel de prioridad del proyecto'),
                'responsible': openapi.Schema(type=openapi.TYPE_INTEGER, description='ID del usuario responsable del proyecto'),
                'detailed_description': openapi.Schema(type=openapi.TYPE_STRING, description='Descripción detallada del proyecto'),
                'type_aplyuni': openapi.Schema(type=openapi.TYPE_STRING, description='Tipo de aplicación (universidad restringida o abierta)'),
                'objectives': openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Items(type=openapi.TYPE_STRING),
                    description='Lista de objetivos del proyecto'
                ),
                'necessary_requirements': openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Items(type=openapi.TYPE_STRING),
                    description='Lista de requisitos necesarios para el proyecto'
                ),
                'progress': openapi.Schema(type=openapi.TYPE_INTEGER, description='Porcentaje de progreso del proyecto'),
                'accepting_applications': openapi.Schema(type=openapi.TYPE_BOOLEAN, description='Indica si el proyecto acepta solicitudes'),
                'name_uniuser': openapi.Schema(type=openapi.TYPE_STRING, description='Nombre de la universidad del usuario responsable'),
            },
            required=['project_id']
        ),
        responses={
            status.HTTP_200_OK: openapi.Response(
                'Proyecto actualizado correctamente',
                openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'project_id': openapi.Schema(type=openapi.TYPE_INTEGER, description='ID del proyecto actualizado'),
                        'name': openapi.Schema(type=openapi.TYPE_STRING, description='Nombre del proyecto'),
                        'description': openapi.Schema(type=openapi.TYPE_STRING, description='Descripción del proyecto'),
                        'start_date': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATE, description='Fecha de inicio'),
                        'end_date': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATE, description='Fecha de finalización'),
                        'status': openapi.Schema(type=openapi.TYPE_STRING, description='Estado del proyecto'),
                        'project_type': openapi.Schema(type=openapi.TYPE_STRING, description='Tipo de proyecto'),
                        'priority': openapi.Schema(type=openapi.TYPE_STRING, description='Prioridad del proyecto'),
                        'responsible': openapi.Schema(type=openapi.TYPE_INTEGER, description='ID del usuario responsable'),
                        'detailed_description': openapi.Schema(type=openapi.TYPE_STRING, description='Descripción detallada'),
                        'type_aplyuni': openapi.Schema(type=openapi.TYPE_STRING, description='Tipo de aplicación'),
                        'objectives': openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            items=openapi.Items(type=openapi.TYPE_STRING),
                            description='Lista de objetivos'
                        ),
                        'necessary_requirements': openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            items=openapi.Items(type=openapi.TYPE_STRING),
                            description='Lista de requisitos necesarios'
                        ),
                        'progress': openapi.Schema(type=openapi.TYPE_INTEGER, description='Porcentaje de progreso del proyecto'),
                        'accepting_applications': openapi.Schema(type=openapi.TYPE_BOOLEAN, description='Indica si se aceptan solicitudes'),
                        'name_uniuser': openapi.Schema(type=openapi.TYPE_STRING, description='Nombre de la universidad asociada al usuario responsable'),
                    },
                ),
            ),
            status.HTTP_404_NOT_FOUND: openapi.Response('Proyecto no encontrado'),
            status.HTTP_400_BAD_REQUEST: openapi.Response('Datos inválidos'),
        },
        tags=["Projects Management"]
    )
    @action(detail=False, methods=['PUT'], url_path='update_project', permission_classes=[IsAuthenticated])
    async def update_project(self, request):

        project_id = request.data.get('project_id')
        if not project_id:
            return Response({"message": "ID del proyecto es requerido."}, status=status.HTTP_400_BAD_REQUEST)

        user_instance = request.user.id

        project = await sync_to_async(get_object_or_404)(Projects, id=project_id, responsible=user_instance)


        serializer = ProjectUpdateSerializer(project, data=request.data, partial=True)
        if await sync_to_async(serializer.is_valid)():
            await sync_to_async(serializer.save)()
            return Response({"status": "Project Update successfully"}, status=status.HTTP_200_OK)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @swagger_auto_schema(
        operation_description="Delete a project by ID",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['id'],
            properties={
                'id': openapi.Schema(type=openapi.TYPE_INTEGER, description='ID of the project to view'),
            },
        ),
        responses={
            status.HTTP_204_NO_CONTENT: openapi.Response('Project deleted successfully'),
            status.HTTP_404_NOT_FOUND: openapi.Response('Project not found'),
        },
        tags=["Projects Management"]
    )
    @action(detail=False, methods=['delete'], url_path='delete_project', permission_classes=[IsAuthenticated])
    async def delete_project(self, request):
        try:

            project_id = request.data.get('id')
            project = await sync_to_async(Projects.objects.get)(pk=project_id)
            await sync_to_async(project.delete)()  
            return Response(status=status.HTTP_204_NO_CONTENT) 
        except Projects.DoesNotExist:
            return Response({"error": "Project not found"}, status=status.HTTP_404_NOT_FOUND)
    
    @swagger_auto_schema(
        operation_description="View project details by ID",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['id'],
            properties={
                'id': openapi.Schema(type=openapi.TYPE_INTEGER, description='ID of the project to view'),
            },
        ),
        responses={
            status.HTTP_200_OK: openapi.Response(
                'Project details retrieved successfully',
                ProjectSerializerID,
            ),
            status.HTTP_404_NOT_FOUND: openapi.Response('Project not found'),
            status.HTTP_400_BAD_REQUEST: openapi.Response('Invalid input data'),
        },
        tags=["Projects Management"]
    )
    @action(detail=False, methods=['POST'], url_path='view_project_id', permission_classes=[IsAuthenticated])
    async def view_project_id(self, request):

        project_id = request.data.get('id')
        user_id = request.user.id 

        if not project_id:

            return Response({"error": "Project ID is required"}, status=status.HTTP_400_BAD_REQUEST)
    
        try:
            project = await sync_to_async(Projects.objects.get)(pk=project_id)
        except Projects.DoesNotExist:

            return Response({"error": "Project not found"}, status=status.HTTP_404_NOT_FOUND)

        creator_name = await self.get_creator_name_view_project_id(project)
        collaboration_count = await self.get_collaboration_count_view_project_id(project)
        responsible_user = await sync_to_async(lambda: Users.objects.filter(id=project.responsible_id).first())()
        has_applied = await self.get_has_applied(user_id, project)

        response_data = {
            'id': project.id,
            'name': project.name,
            'description': project.description,
            'start_date': project.start_date.isoformat(),
            'end_date': project.end_date.isoformat() if project.end_date else None,
            'status': project.status,
            'project_type': project.project_type,
            'priority': project.priority,
            'responsible': project.responsible_id if project.responsible_id else None,
            'name_uniuser': project.name_uniuser,
            'detailed_description': project.detailed_description,
            'photo': responsible_user.photo,
            'necessary_requirements': project.necessary_requirements,
            'progress': project.progress,
            'objectives': project.objectives,
            'accepting_applications': project.accepting_applications,
            'type_aplyuni': project.type_aplyuni,
            'creator_name': creator_name,
            'collaboration_count': collaboration_count,
            'has_applied': has_applied,
        }

        return Response(response_data, status=status.HTTP_200_OK)

    async def get_creator_name_view_project_id(self, obj):

        if obj.responsible_id: 
            authuser = await sync_to_async(User.objects.get)(id=obj.responsible_id)
            if authuser:
                return f"{authuser.first_name} {authuser.last_name}"
        return None

    async def get_collaboration_count_view_project_id(self, obj):
        count = await sync_to_async(Collaborations.objects.filter(project=obj).count)()
        return count
    
    async def get_has_applied(self, user_id, project):
    
        try:
    
            if project.responsible_id == user_id:
                return True  
            
            
            application = await sync_to_async(lambda: Solicitudes.objects.filter(
                id_user=user_id,
                id_project=project
            ).first())()

            if application:
                if application.status == 'Pendiente':
                    return True
                elif application.status == 'Aceptada':
                    return True
            return False  # User has not applied
        except Exception:
            return False
    
    @swagger_auto_schema(
        operation_description="Retrieve all projects in ascending order by start date",
        responses={
            status.HTTP_200_OK: openapi.Response(
                description="List of projects in ascending order",
                schema=ProjectSerializerAll(many=True)
            ),
            status.HTTP_400_BAD_REQUEST: "Invalid request",
        },
        tags=["Projects Management"]
    )
    @action(detail=False, methods=['GET'], url_path='view_project_all', permission_classes=[IsAuthenticated])
    async def view_project_all(self, request):
        try:

            projects = await sync_to_async(list)(Projects.objects.all().order_by('-id'))

            project_data = []
            for project in projects:

                creator_name = await self.get_creator_name(project)
                responsible_user = await sync_to_async(lambda: Users.objects.filter(id=project.responsible_id).first())()
                collaboration_count = await self.get_collaboration_count(project)

                project_dict = {
                    'id': project.id,
                    'name': project.name,
                    'description': project.description,
                    'start_date': project.start_date,
                    'end_date': project.end_date,
                    'status': project.status,
                    'project_type': project.project_type,
                    'priority': project.priority,
                    'responsible': project.responsible_id,
                    'name_uniuser': project.name_uniuser,
                    'photo': responsible_user.photo,
                    'detailed_description': project.detailed_description,
                    'progress': project.progress,
                    'accepting_applications': project.accepting_applications,
                    'type_aplyuni': project.type_aplyuni,
                    'creator_name': creator_name,
                    'collaboration_count': collaboration_count,
                }
                project_data.append(project_dict)

            return Response(project_data, status=status.HTTP_200_OK)

        except Exception as e:

            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @swagger_auto_schema(
        operation_description="Retrieve the 3 most recent projects in descending order by start date",
        responses={
            status.HTTP_200_OK: openapi.Response(
                description="List of the 3 most recent projects",
                schema=ProjectSerializerAll(many=True)
            ),
            status.HTTP_400_BAD_REQUEST: "Invalid request",
        },
        tags=["Projects Management"]
    )
    @action(detail=False, methods=['GET'], url_path='view_recent_projects', permission_classes=[IsAuthenticated])
    async def view_recent_projects(self, request):
 
        try:
 
            projects = await sync_to_async(list)(Projects.objects.all().order_by('-id')[:3])

            project_data = []
            for project in projects:

                creator_name = await self.get_creator_name(project)
                responsible_user = await sync_to_async(lambda: Users.objects.filter(id=project.responsible_id).first())()
                collaboration_count = await self.get_collaboration_count(project)

                project_dict = {
                    'id': project.id,
                    'name': project.name,
                    'description': project.description,
                    'start_date': project.start_date,
                    'end_date': project.end_date,
                    'status': project.status,
                    'project_type': project.project_type,
                    'priority': project.priority,
                    'responsible': project.responsible_id,
                    'photo': responsible_user.photo,
                    'name_uniuser': project.name_uniuser,
                    'detailed_description': project.detailed_description,
                    'progress': project.progress,
                    'accepting_applications': project.accepting_applications,
                    'type_aplyuni': project.type_aplyuni,
                    'creator_name': creator_name,
                    'collaboration_count': collaboration_count,
                }
                project_data.append(project_dict)

            return Response(project_data, status=status.HTTP_200_OK)

        except Exception as e:

            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
           
    async def get_creator_name(self, obj):
        if obj.responsible_id: 
            authuser = await sync_to_async(User.objects.get)(id=obj.responsible_id)
            if authuser:
                return f"{authuser.first_name} {authuser.last_name}"
        return None

    async def get_collaboration_count(self, obj):
        count = await sync_to_async(Collaborations.objects.filter(project=obj).count)()
        return count

    @swagger_auto_schema(
        operation_summary="Obtener proyectos creados por el usuario autenticado",
        operation_description="Recupera todos los proyectos creados por el usuario autenticado.",
        responses={
            status.HTTP_200_OK: openapi.Response(
                'Lista de proyectos creados por el usuario',
                openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Schema(
                        type=openapi.TYPE_OBJECT,
                        properties={
                            'id': openapi.Schema(type=openapi.TYPE_INTEGER, description='ID del proyecto'),
                            'name': openapi.Schema(type=openapi.TYPE_STRING, description='Nombre del proyecto'),
                            'description': openapi.Schema(type=openapi.TYPE_STRING, description='Descripción del proyecto'),
                            'start_date': openapi.Schema(type=openapi.TYPE_STRING, format='date', description='Fecha de inicio del proyecto'),
                            'end_date': openapi.Schema(type=openapi.TYPE_STRING, format='date', description='Fecha de finalización del proyecto'),
                            'status': openapi.Schema(type=openapi.TYPE_STRING, description='Estado del proyecto'),
                            'project_type': openapi.Schema(type=openapi.TYPE_STRING, description='Tipo de proyecto'),
                            'priority': openapi.Schema(type=openapi.TYPE_STRING, description='Prioridad del proyecto'),
                            'responsible': openapi.Schema(type=openapi.TYPE_INTEGER, description='ID del responsable del proyecto'),
                            'name_responsible': openapi.Schema(type=openapi.TYPE_STRING, description='Nombre del responsable del proyecto'),
                            'detailed_description': openapi.Schema(type=openapi.TYPE_STRING, description='Descripción detallada del proyecto'),
                            'type_aplyuni': openapi.Schema(type=openapi.TYPE_STRING, description='Tipo de aplicación universitaria'),
                            'objectives': openapi.Schema(type=openapi.TYPE_STRING, description='Objetivos del proyecto'),
                            'necessary_requirements': openapi.Schema(type=openapi.TYPE_STRING, description='Requisitos necesarios para el proyecto'),
                            'progress': openapi.Schema(type=openapi.TYPE_STRING, description='Progreso del proyecto'),
                            'accepting_applications': openapi.Schema(type=openapi.TYPE_BOOLEAN, description='Si el proyecto está aceptando aplicaciones'),
                            'name_uniuser': openapi.Schema(type=openapi.TYPE_STRING, description='Nombre del usuario universitario'),
                            'collaboration_count': openapi.Schema(type=openapi.TYPE_INTEGER, description='Número de colaboraciones en el proyecto'),
                            'collaborators': openapi.Schema(
                                type=openapi.TYPE_ARRAY,
                                items=openapi.Schema(
                                    type=openapi.TYPE_OBJECT,
                                    properties={
                                        'id': openapi.Schema(type=openapi.TYPE_INTEGER, description='ID del colaborador'),
                                        'name': openapi.Schema(type=openapi.TYPE_STRING, description='Nombre del colaborador')
                                    }
                                )
                            ),
                            'responsible_photo': openapi.Schema(type=openapi.TYPE_STRING, description='Foto del responsable del proyecto')
                        }
                    )
                )
            ),
            status.HTTP_404_NOT_FOUND: openapi.Response(
                'No se encontraron proyectos',
                openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'message': openapi.Schema(type=openapi.TYPE_STRING, description='Mensaje de error')
                    }
                )
            ),
        },
        tags=["Projects Management"]
    )
    @action(detail=False, methods=['GET'], url_path='get_user_created_projects', permission_classes=[IsAuthenticated])
    async def get_user_created_projects(self, request):
        user_id = request.user.id  

        projects = await sync_to_async(list)(Projects.objects.filter(responsible=user_id))
        
        if projects:
            response_data = []
            for project in projects:
                collaboratorsall = await sync_to_async(list)(Collaborations.objects.filter(project=project).select_related('user__authuser'))
                
                collaborators_info = await self.get_collaborators_info_proyect(collaboratorsall)
                name_responsible = await self.get_responsible_name_proyect(project)
                collaboration_count = await self.get_collaboration_count_proyect(project)

                responsible_user = await sync_to_async(Users.objects.get)(id=project.responsible_id)
                responsible_photo = responsible_user.photo if responsible_user.photo else None

                project_data = {
                    'id': project.id,
                    'name': project.name,
                    'description': project.description,
                    'start_date': project.start_date,
                    'end_date': project.end_date,
                    'status': project.status,
                    'project_type': project.project_type,
                    'priority': project.priority,
                    'responsible': project.responsible_id,  
                    'name_responsible': name_responsible,
                    'detailed_description': project.detailed_description,
                    'type_aplyuni': project.type_aplyuni,
                    'objectives': project.objectives,
                    'necessary_requirements': project.necessary_requirements,
                    'progress': project.progress,
                    'accepting_applications': project.accepting_applications,
                    'name_uniuser': project.name_uniuser,
                    'collaboration_count': collaboration_count,
                    'collaborators': collaborators_info,
                    'responsible_photo': responsible_photo,  
                }
                response_data.append(project_data)

            return Response(response_data, status=status.HTTP_200_OK)
        else:
            return Response({"message": "No se encontraron proyectos"}, status=status.HTTP_404_NOT_FOUND)

    @swagger_auto_schema(
        operation_description="Obtener un proyecto específico pasando el ID del proyecto en el cuerpo de la solicitud",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'project_id': openapi.Schema(type=openapi.TYPE_INTEGER, description='ID del proyecto'),
            },
            required=['project_id']
        ),
        responses={
            status.HTTP_200_OK: openapi.Response('Proyecto encontrado'),
            status.HTTP_404_NOT_FOUND: openapi.Response('Proyecto no encontrado'),
        },
        tags=["Projects Management"]
    )
    @action(detail=False, methods=['POST'], url_path='get-project-id', permission_classes=[IsAuthenticated])
    async def get_project_id(self, request):
        project_id = request.data.get('id_project')
        if not project_id:
            return Response({"message": "ID del proyecto es requerido."}, status=status.HTTP_400_BAD_REQUEST)

        projects = await sync_to_async(Projects.objects.filter(id=project_id).first)()
        
        if projects:

                collaboratorsall = await sync_to_async(list)(Collaborations.objects.filter(project=projects).select_related('user__authuser'))
                collaborators_info = await self.get_collaborators_info_proyect(collaboratorsall)

                name_responsible = await self.get_responsible_name_proyect(projects)

                collaboration_count = await self.get_collaboration_count(projects)

                responsible_photo = await sync_to_async(lambda: Users.objects.filter(id=projects.responsible_id).first())()
                
                project_data = {
                    'id': projects.id,
                    'name': projects.name,
                    'description': projects.description,
                    'start_date': projects.start_date,
                    'end_date': projects.end_date,
                    'status': projects.status,
                    'project_type': projects.project_type,
                    'priority': projects.priority,
                    'responsible': projects.responsible_id,  
                    'name_responsible': name_responsible,
                    'detailed_description': projects.detailed_description,
                    'type_aplyuni': projects.type_aplyuni,
                    'objectives': projects.objectives,
                    'necessary_requirements': projects.necessary_requirements,
                    'progress': projects.progress,
                    'accepting_applications': projects.accepting_applications,
                    'name_uniuser': projects.name_uniuser,
                    'collaboration_count': collaboration_count,
                    'collaborators': collaborators_info,
                    'responsible_photo': responsible_photo.photo, 
                }

                return Response(project_data, status=status.HTTP_200_OK)
        else:
            return Response({"message": "No se encontraron proyectos"}, status=status.HTTP_404_NOT_FOUND)
        
    async def get_collaboration_count_proyect(self, project):
        return await sync_to_async(lambda: Collaborations.objects.filter(project=project).count())()

    async def get_collaborators_info_proyect(self, collaborators):
        collaborator_info = []
        for collab in collaborators:
            if collab.user and collab.user.authuser:
                
                photo = await sync_to_async(lambda: Users.objects.filter(id=collab.user.authuser.id).first())()
                
                user_info = {
                    "id": collab.user.id,
                    "photo" : photo.photo,
                    "name": f"{collab.user.authuser.first_name} {collab.user.authuser.last_name}"
                }
                collaborator_info.append(user_info)
        return collaborator_info

    async def get_responsible_name_proyect(self, obj):
        
        if obj.responsible_id: 
            authuser = await sync_to_async(User.objects.get)(id=obj.responsible_id)
            if authuser:
                return f"{authuser.first_name} {authuser.last_name}"    
        
class FormsViewSet(ViewSet): #(Form Management) 
    @swagger_auto_schema(
        operation_description="Crear un nuevo formulario",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['title', 'url', 'created_end'],
            properties={
                'title': openapi.Schema(type=openapi.TYPE_STRING, description='Título del formulario'),
                'url': openapi.Schema(type=openapi.TYPE_STRING, description='URL del formulario'),
            },
        ),
        responses={
            status.HTTP_201_CREATED: openapi.Response(
                'Formulario creado exitosamente',
                openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'id': openapi.Schema(type=openapi.TYPE_INTEGER, description='ID del formulario creado'),
                        'title': openapi.Schema(type=openapi.TYPE_STRING, description='Título del formulario'),
                        'url': openapi.Schema(type=openapi.TYPE_STRING, description='URL del formulario'),
                        'created_at': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATETIME, description='Fecha de creación del formulario'),
                        'created_end': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATETIME, description='Fecha de finalización del formulario'),
                        'user_id': openapi.Schema(type=openapi.TYPE_INTEGER, description='ID del usuario que creó el formulario'),
                    },
                ),
            ),
            status.HTTP_400_BAD_REQUEST: openapi.Response('Datos inválidos en la solicitud'),
        },
        tags=["Form Management"]
    )
    @action(detail=False, methods=['POST'], url_path='create_form', permission_classes=[IsAuthenticated])
    async def create_form(self, request):
        
        user_id = request.user.id

        form_data = {
            **request.data,
            'created_at': timezone.now().strftime('%Y-%m-%d'),  
            'user': user_id,  
        }

        form_serializer = FormSerializer(data=form_data)

        if await sync_to_async(form_serializer.is_valid)():
            await sync_to_async(form_serializer.save)()
            return Response(form_serializer.data, status=status.HTTP_201_CREATED)

        return Response(form_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @swagger_auto_schema(
        operation_description="Obtener todos los formularios con los nombres de los usuarios",
        responses={
            status.HTTP_200_OK: openapi.Response(
                'Lista de formularios',
                openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Schema(
                        type=openapi.TYPE_OBJECT,
                        properties={
                            'id': openapi.Schema(type=openapi.TYPE_INTEGER, description='ID del formulario'),
                            'title': openapi.Schema(type=openapi.TYPE_STRING, description='Título del formulario'),
                            'url': openapi.Schema(type=openapi.TYPE_STRING, description='URL del formulario'),
                            'created_at': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATETIME, description='Fecha de creación del formulario'),
                            'created_end': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATETIME, description='Fecha de finalización del formulario'),
                            'user_id': openapi.Schema(type=openapi.TYPE_INTEGER, description='ID del usuario que creó el formulario'),
                            'first_name': openapi.Schema(type=openapi.TYPE_STRING, description='Nombre del usuario'),
                            'last_name': openapi.Schema(type=openapi.TYPE_STRING, description='Apellido del usuario'),
                        },
                    ),
                ),
            ),
            status.HTTP_400_BAD_REQUEST: openapi.Response('Error en la solicitud'),
        },
        tags=["Form Management"]
    )
    @action(detail=False, methods=['GET'], url_path='get_all_forms', permission_classes=[IsAuthenticated])
    async def get_all_forms(self, request):
        
        forms = await self.get_forms()
        data = []

        for form in forms:
            form_data = FormSerializer(form).data
            user = await self.get_user(form.user_id)
            form_data['first_name'] = user.first_name
            form_data['last_name'] = user.last_name
            data.append(form_data)

        return Response(data, status=status.HTTP_200_OK)

    async def get_forms(self):
        return await sync_to_async(list)(Forms.objects.all().order_by('-created_at'))

    async def get_user(self, user_id):
        return await sync_to_async(User.objects.get)(id=user_id)
    
    @swagger_auto_schema(
        operation_description="Eliminar un formulario existente",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['id'],
            properties={
                'id': openapi.Schema(type=openapi.TYPE_INTEGER, description='ID del formulario a eliminar'),
            },
        ),
        responses={
            status.HTTP_204_NO_CONTENT: openapi.Response('Formulario eliminado exitosamente'),
            status.HTTP_404_NOT_FOUND: openapi.Response('Formulario no encontrado'),
            status.HTTP_403_FORBIDDEN: openapi.Response('No tienes permiso para eliminar este formulario'),
        },
        tags=["Form Management"]
    )
    @action(detail=False, methods=['DELETE'], url_path='delete_form', permission_classes=[IsAuthenticated])
    async def delete_form(self, request):

        form_id = request.data.get('id')

        form = await self.get_form(form_id)

        if form is None:
            return Response({'detail': 'Formulario no encontrado.'}, status=status.HTTP_404_NOT_FOUND)
        
        if form.user_id != request.user.id:
            return Response({'detail': 'No tiene permiso para eliminar este formulario.'}, status=status.HTTP_403_FORBIDDEN)

        await sync_to_async(form.delete)()

        return Response(status=status.HTTP_204_NO_CONTENT)

    async def get_form(self, form_id):
        return await sync_to_async(Forms.objects.get)(id=form_id)

class UserAchievementsViewSet(ViewSet): #(UserAchievements Management)

    @swagger_auto_schema(
        operation_description="Validar logros de un usuario y almacenarlos",
        responses={
            status.HTTP_200_OK: openapi.Response('Logros validados y almacenados'),
            status.HTTP_400_BAD_REQUEST: openapi.Response('Error en la solicitud'),
        },
        tags=["UserAchievements Management"]
    )
    @action(detail=False, methods=['POST'],  url_path='validate_achievements', permission_classes=[IsAuthenticated])
    def validate_achievements(self, request):
        user = request.user 
        unlocked_achievements = []

        try:
            achievements = Achievements.objects.all()
            for achievement in achievements:
                unlocked = False

                if achievement.id == 1:  # Primera Gran Misión
                    unlocked = Projects.objects.filter(responsible=user.id).exists()
                elif achievement.id == 2:  # Manos a la Obra
                    unlocked = Projects.objects.filter(status='En progreso', responsible=user.id).count() >= 2
                elif achievement.id == 3:  # Incansable Constructor
                    unlocked = Projects.objects.filter(status='Completado', responsible=user.id).count() >= 5
                elif achievement.id == 4:  # Siempre al Liderazgo
                    unlocked = Projects.objects.filter(responsible=user.id).count() >= 3
                elif achievement.id == 5:  # Compromiso sin Fronteras
                    user_instance = Users.objects.get(authuser=user)
                    unlocked = Collaborations.objects.filter(user=user_instance.id).select_related('project__responsible').values('project__responsible__university').distinct().count() >= 3
                elif achievement.id == 6:  # Multitasker
                    unlocked = Projects.objects.filter(status='En progreso', responsible=user.id).count() >= 3
                elif achievement.id == 7:  # Colaborador Compulsivo
                    unlocked = Collaborations.objects.filter(user=user.id).count() >= 10
                elif achievement.id == 8:  # Maestro de Roles
                    # Verifica si el usuario tiene más de una colaboración única en proyectos
                    collaborations_count = Collaborations.objects.filter(user=user.id).values('project').annotate(unique_roles=Count('role')).count()
                    projects_count = Projects.objects.filter(responsible=user.id).count()
                    # Desbloquea el logro si hay colaboraciones y es responsable de al menos un proyecto
                    unlocked = collaborations_count > 0 and projects_count > 0
                elif achievement.id == 9:  # Líder Experto
                    unlocked = Projects.objects.filter(status='Completado', responsible=user.id).count() >= 5
                elif achievement.id == 10:  # Desarrollador Incansable
                    unlocked = Projects.objects.filter(status='Completado', project_type__contains=['Desarrollo de Software'], responsible=user.id).count() >= 3
                elif achievement.id == 11:  # Investigador Académico
                    unlocked = Projects.objects.filter(status='Completado', project_type__contains=['Investigación Académica'], responsible=user.id).count() >= 2
                elif achievement.id == 12:  # Creador Ecológico
                    unlocked = Projects.objects.filter(status='Completado', project_type__contains=['Ambiental'], responsible=user.id).count() >= 3
                elif achievement.id == 13:  # Analista de Datos
                    unlocked = Projects.objects.filter(status='Completado', project_type__contains=['Análisis de Datos'], responsible=user.id).count() >= 2
                elif achievement.id == 14:  # Planificador Estratégico
                    unlocked = Projects.objects.filter(status='Completado', project_type__contains=['Planificación y Gestión'], responsible=user.id).count() >= 1
                elif achievement.id == 15:  # Innovador del Futuro
                    unlocked = Projects.objects.filter(status='Completado', project_type__contains=['Innovación o Emprendimiento'], responsible=user.id).count() >= 2

                if unlocked:
                # Verificar si el logro ya ha sido desbloqueado por el usuario
                    if not UserAchievements.objects.filter(user=user.id, achievement=achievement).exists():
                        unlocked_achievements.append(achievement.id)

                        # Guardar en UserAchievements
                        user_achievement_data = {
                            'user': user.id,  # Asignar el ID del usuario autenticado
                            'achievement': achievement.id,  # Asignar el ID del logro
                            'unlocked': True,  # Estado de desbloqueo
                        }

                        # Serializa los datos
                        user_achievement_serializer = UserAchievementsSerializer(data=user_achievement_data)

                        # Guarda si los datos son válidos
                        if user_achievement_serializer.is_valid():
                            user_achievement_serializer.save()
                        else:
                            return Response(user_achievement_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

            return Response({'unlocked_achievements': unlocked_achievements}, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
          
    @swagger_auto_schema(
        operation_description="Obtener todos los logros del usuario",
        responses={
            status.HTTP_200_OK: openapi.Response(
                'Lista de logros',
                openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'user': openapi.Schema(type=openapi.TYPE_INTEGER, description='ID del usuario'),
                        'first_name': openapi.Schema(type=openapi.TYPE_STRING, description='Nombre del usuario'),
                        'last_name': openapi.Schema(type=openapi.TYPE_STRING, description='Apellido del usuario'),
                        'achievements': openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            items=openapi.Schema(
                                type=openapi.TYPE_OBJECT,
                                properties={
                                    'id': openapi.Schema(type=openapi.TYPE_INTEGER, description='ID del logro del usuario'),
                                    'achievement': openapi.Schema(type=openapi.TYPE_INTEGER, description='ID del logro correspondiente'),
                                    'unlocked': openapi.Schema(type=openapi.TYPE_BOOLEAN, description='Estado del logro (desbloqueado o no)'),
                                },
                            ),
                        ),
                    },
                ),
            ),
            status.HTTP_400_BAD_REQUEST: openapi.Response('Error en la solicitud'),
        },
        tags=["UserAchievements Management"]
    )
    @action(detail=False, methods=['GET'], url_path='list_user_achievements', permission_classes=[IsAuthenticated])
    def list_user_achievements(self, request):
        user = request.user
        user_achievements = UserAchievements.objects.filter(user=user.id)
        
        user_photo = Users.objects.filter(authuser=user.id).values_list('photo', flat=True).first()
        
        achievements_data = [
            {
                "achievement": achievement.achievement.id,
                "unlocked": achievement.unlocked,
                "name": achievement.achievement.name,
                "description": achievement.achievement.description
            }
            for achievement in user_achievements
        ]

        response_data = {
            "user": user.id,
            "first_name": user.first_name,
            "photo": user_photo,   
            "last_name": user.last_name,
            "achievements": achievements_data
        }

        return Response(response_data, status=status.HTTP_200_OK)
    
    @swagger_auto_schema(
        operation_description="Obtener todos los logros de un usuario específico",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'user_id': openapi.Schema(type=openapi.TYPE_INTEGER, description="ID del usuario"),
            },
            required=['user_id']
        ),
        responses={
            status.HTTP_200_OK: openapi.Response(
                'Lista de logros',
                openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Schema(
                        type=openapi.TYPE_OBJECT,
                        properties={
                            'id': openapi.Schema(type=openapi.TYPE_INTEGER, description='ID del logro del usuario'),
                            'achievement': openapi.Schema(type=openapi.TYPE_INTEGER, description='ID del logro correspondiente'),
                            'unlocked': openapi.Schema(type=openapi.TYPE_BOOLEAN, description='Estado del logro (desbloqueado o no)'),
                            'user': openapi.Schema(type=openapi.TYPE_INTEGER, description='ID del usuario al que pertenece el logro'),
                            'first_name': openapi.Schema(type=openapi.TYPE_STRING, description="Nombre del usuario"),
                            'last_name': openapi.Schema(type=openapi.TYPE_STRING, description="Apellido del usuario"),
                        },
                    ),
                ),
            ),
            status.HTTP_400_BAD_REQUEST: openapi.Response('Error en la solicitud'),
        },
        tags=["UserAchievements Management"]
    )
    @action(detail=False, methods=['POST'], url_path='list_user_achievements_id', permission_classes=[IsAuthenticated])
    def list_user_achievements_id(self, request):
        user_id = request.data.get('user_id')
        user = Users.objects.filter(id=user_id).select_related('authuser').first()

        if not user:
            return Response({"error": "Usuario no encontrado."}, status=status.HTTP_400_BAD_REQUEST)

        user_achievements = UserAchievements.objects.filter(user=user.id)

        user_photo = user.photo if user.photo else None

        achievements_data = [
            {
                "achievement": achievement.achievement.id,
                "unlocked": achievement.unlocked,
                "name": achievement.achievement.name,
                "description": achievement.achievement.description
            }
            for achievement in user_achievements
        ]

        response_data = {
            "user": user.id,
            "first_name": user.authuser.first_name,
            "last_name": user.authuser.last_name,
            "photo": user_photo,
            "achievements": achievements_data
        }

        return Response(response_data, status=status.HTTP_200_OK)
    
    @swagger_auto_schema(
        operation_description="Obtener todos los logros",
        responses={
            status.HTTP_200_OK: openapi.Response('Lista de logros', AchievementsSerializer(many=True)),
            status.HTTP_404_NOT_FOUND: openapi.Response('No se encontraron logros'),
        },
        tags=["UserAchievements Management"]
    )
    @action(detail=False, methods=['GET'], url_path='all_achievements', permission_classes=[IsAuthenticated])
    async def get_all_achievements(self, request):

        achievements = await self.get_achievements()
        
        if not achievements:
            return Response({'detail': 'No se encontraron logros.'}, status=status.HTTP_404_NOT_FOUND)

        serializer = AchievementsSerializer(achievements, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    async def get_achievements(self):
        return await sync_to_async(list)(Achievements.objects.all())
    
    @swagger_auto_schema(
        operation_description="Obtener todos los logros disponibles",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['user_id'],
            properties={
                'user_id': openapi.Schema(type=openapi.TYPE_INTEGER, description='ID del usuario'),
            },
        ),
        responses={
            status.HTTP_200_OK: openapi.Response('Lista de logros disponibles', AchievementsSerializer(many=True)),
            status.HTTP_404_NOT_FOUND: openapi.Response('Usuario no encontrado'),
            status.HTTP_400_BAD_REQUEST: openapi.Response('ID de usuario inválido'),
        },
        tags=["UserAchievements Management"]
    )
    @action(detail=False, methods=['POST'], url_path='get_all_achievements_id', permission_classes=[IsAuthenticated])
    async def get_all_achievements_id(self, request):
        user_id = request.data.get('user_id')

        if user_id is None:
            return Response({'detail': 'ID de usuario inválido.'}, status=status.HTTP_400_BAD_REQUEST)

        user_exists = await self.check_user_exists(user_id)
        
        if not user_exists:
            return Response({'detail': 'Usuario no encontrado.'}, status=status.HTTP_404_NOT_FOUND)

        achievements = await self.get_all_achievements()

        serializer = AchievementsSerializer(achievements, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    async def check_user_exists(self, user_id):

        return await sync_to_async(Users.objects.filter(id=user_id).exists)()

    async def get_all_achievements(self):

        return await sync_to_async(list)(Achievements.objects.all())
    
class ApplicationsViewSet(ViewSet): #(Applications Management)

    @swagger_auto_schema(
        operation_summary="Aplicar a un proyecto",
        operation_description="Permite a un usuario aplicar a un proyecto específico.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['project_id', 'message'],
            properties={
                'project_id': openapi.Schema(type=openapi.TYPE_INTEGER, description='ID del proyecto'),
                'message': openapi.Schema(type=openapi.TYPE_STRING, description='Mensaje de la solicitud')
            }
        ),
        responses={
            status.HTTP_201_CREATED: openapi.Response(
                'Solicitud y notificación creadas exitosamente',
                openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'solicitud': openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                'id_user': openapi.Schema(type=openapi.TYPE_INTEGER, description='ID del usuario que aplicó'),
                                'id_project': openapi.Schema(type=openapi.TYPE_INTEGER, description='ID del proyecto'),
                                'status': openapi.Schema(type=openapi.TYPE_STRING, description='Estado de la solicitud'),
                                'name_lider': openapi.Schema(type=openapi.TYPE_STRING, description='Nombre del líder del proyecto'),
                                'created_at': openapi.Schema(type=openapi.TYPE_STRING, format='date', description='Fecha de creación de la solicitud'),
                                'name_project': openapi.Schema(type=openapi.TYPE_STRING, description='Nombre del proyecto'),
                                'name_user': openapi.Schema(type=openapi.TYPE_STRING, description='Nombre del usuario que aplicó'),
                                'message': openapi.Schema(type=openapi.TYPE_STRING, description='Mensaje de la solicitud')
                            }
                        ),
                        'notificación': openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                'user': openapi.Schema(type=openapi.TYPE_INTEGER, description='ID del usuario que recibe la notificación'),
                                'message': openapi.Schema(type=openapi.TYPE_STRING, description='Mensaje de la notificación'),
                                'is_read': openapi.Schema(type=openapi.TYPE_INTEGER, description='Estado de lectura de la notificación (0 o 1)'),
                                'created_at': openapi.Schema(type=openapi.TYPE_STRING, format='date-time', description='Fecha de creación de la notificación'),
                                'sender': openapi.Schema(type=openapi.TYPE_INTEGER, description='ID del usuario que envió la notificación')
                            }
                        )
                    }
                )
            ),
            status.HTTP_400_BAD_REQUEST: openapi.Response('Error en los datos proporcionados'),
            status.HTTP_404_NOT_FOUND: openapi.Response('Proyecto no encontrado'),
        },
        tags=["Applications Management"]
    )
    @action(detail=False, methods=['POST'], url_path='ApplyProject', permission_classes=[IsAuthenticated])
    async def ApplyProject(self, request):
            project_id = request.data.get('project_id')
            message = request.data.get('message')
            user = request.user
            
            try:
                project = await sync_to_async(Projects.objects.get)(id=project_id)
                if not project.accepting_applications:
                    return Response({"error": "Este proyecto no está aceptando aplicaciones"}, status=status.HTTP_400_BAD_REQUEST)

                existing_solicitud = await sync_to_async(Solicitudes.objects.filter(id_user=user.id, id_project=project_id).first)()
                if existing_solicitud:
                    return Response({"error": "Ya has aplicado a este proyecto."}, status=status.HTTP_400_BAD_REQUEST)
                
                lider_id = project.responsible_id  
                
                lider = await sync_to_async(User.objects.get)(id=lider_id)  
                
                photo = await sync_to_async(lambda: Users.objects.filter(id = user.id).first())()

                name_lider = f"{lider.first_name} {lider.last_name}"

                solicitud_data = {
                    'id_user': user.id,
                    'name_lider': name_lider,
                    'created_at': timezone.now().strftime('%Y-%m-%d'),
                    'id_project': project.id,
                    "message" : message,
                    'status': 'Pendiente',
                    'photo' : photo.photo,
                    'name_project': project.name,
                    'name_user': f"{user.first_name} {user.last_name}",
                }

                solicitud_serializer = SolicitudSerializer(data=solicitud_data)

                if await sync_to_async(solicitud_serializer.is_valid)():
                    await sync_to_async(solicitud_serializer.save)()
                
                    notification_data = {
                        'sender': user.id,  
                        'message': f"{user.first_name} {user.last_name} aplico al proyecto '{project.name}' ",
                        'is_read': 0,
                        'created_at': timezone.now(),
                        'user_id': lider_id
                    }
                    notification_serializer = NotificationSerializer(data=notification_data)
                    
                    if await sync_to_async(notification_serializer.is_valid)():
                        await sync_to_async(notification_serializer.save)()
                    else:
                        return Response(notification_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

                    return Response(solicitud_serializer.data, status=status.HTTP_201_CREATED)
                else:
                    return Response(solicitud_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

            except Projects.DoesNotExist:
                return Response({"error": "Proyecto no encontrado"}, status=status.HTTP_404_NOT_FOUND)
            except User.DoesNotExist:
                return Response({"error": "Líder del proyecto no encontrado"}, status=status.HTTP_404_NOT_FOUND)
            except Exception as e:
                return Response({"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @swagger_auto_schema(
        operation_summary="Aceptar solicitud de un proyecto",
        operation_description="Permite a un usuario aceptar una solicitud de un proyecto específico.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['id_solicitud'],
            properties={
                'id_solicitud': openapi.Schema(type=openapi.TYPE_INTEGER, description='ID de la solicitud'),
            }
        ),
        responses={
            status.HTTP_200_OK: openapi.Response(
                'Solicitud aceptada exitosamente',
                openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'mensaje': openapi.Schema(type=openapi.TYPE_STRING, description='Mensaje de éxito')
                    }
                )
            ),
            status.HTTP_400_BAD_REQUEST: openapi.Response('Error en los datos proporcionados'),
            status.HTTP_403_FORBIDDEN: openapi.Response('No tienes permiso para aceptar esta solicitud'),
            status.HTTP_404_NOT_FOUND: openapi.Response('Solicitud no encontrada'),
        },
        tags=["Applications Management"]
    )
    @action(detail=False, methods=['POST'], url_path='AcceptProject',permission_classes=[IsAuthenticated])
    async def AcceptProject(self, request):
        id_solicitud = request.data.get('id_solicitud')
        user = request.user
        try:
            solicitud = await sync_to_async(Solicitudes.objects.select_related('id_project', 'id_user').get)(id_solicitud=id_solicitud)

            project_responsible_id = solicitud.id_project

            project_responsible_user_id = await sync_to_async(lambda: project_responsible_id.responsible)()

            if project_responsible_user_id.id != user.id:
                return Response({"error": "No tienes permiso para aceptar esta solicitud"}, status=status.HTTP_403_FORBIDDEN)
            
            solicitud.status = 'Aceptada'
            await sync_to_async(solicitud.save)()

            collaboration_data = {
                'user': solicitud.id_user.id,
                'project': solicitud.id_project.id,
                'status': 'Activa'
            }
            collaboration_serializer = CollaboratorSerializer(data=collaboration_data)
            
            if await sync_to_async(collaboration_serializer.is_valid)():
                await sync_to_async(collaboration_serializer.save)()

                notification_data = {
                    'sender': user.id, 
                    'message': f"Tu solicitud al proyecto '{solicitud.id_project.name}' ha sido aceptada.",
                    'is_read': 0,
                    'created_at': timezone.now(),
                    'user_id': solicitud.id_user.id  
                }
                notification_serializer = NotificationSerializer(data=notification_data)
                
                if await sync_to_async(notification_serializer.is_valid)():
                    await sync_to_async(notification_serializer.save)()
                else:
                    return Response(notification_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
                
                return Response({"mensaje": "Solicitud aceptada y colaboración creada exitosamente"}, status=status.HTTP_200_OK)
            else:
                return Response(collaboration_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        except Solicitudes.DoesNotExist:
            return Response({"error": "Solicitud no encontrada"}, status=status.HTTP_404_NOT_FOUND)

    @swagger_auto_schema(
        operation_summary="Negar solicitud de un proyecto",
        operation_description="Permite a un usuario negar una solicitud de un proyecto específico.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['id_solicitud'],
            properties={
                'id_solicitud': openapi.Schema(type=openapi.TYPE_INTEGER, description='ID de la solicitud'),
            }
        ),
        responses={
            status.HTTP_200_OK: openapi.Response(
                'Solicitud negada exitosamente',
                openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'mensaje': openapi.Schema(type=openapi.TYPE_STRING, description='Mensaje de éxito')
                    }
                )
            ),
            status.HTTP_400_BAD_REQUEST: openapi.Response('Error en los datos proporcionados'),
            status.HTTP_403_FORBIDDEN: openapi.Response('No tienes permiso para negar esta solicitud'),
            status.HTTP_404_NOT_FOUND: openapi.Response('Solicitud no encontrada'),
        },
        tags=["Applications Management"]
    )
    @action(detail=False, methods=['POST'], url_path='Denyproject',permission_classes=[IsAuthenticated])
    async def Denyproject(self, request):
        solicitud_id = request.data.get('id_solicitud')
        user = request.user
        try:
            solicitud = await sync_to_async(Solicitudes.objects.select_related('id_project', 'id_user').get)(id_solicitud=solicitud_id)

            project_responsible_id = solicitud.id_project

            project_responsible_user_id = await sync_to_async(lambda: project_responsible_id.responsible)()

            if project_responsible_user_id.id != user.id:
                return Response({"error": "No tienes permiso para aceptar esta solicitud"}, status=status.HTTP_403_FORBIDDEN)

            solicitud.status = 'Rechazado'
            await sync_to_async(solicitud.save)()
            
            notification_data = {
                'sender': user.id,  
                'message': f"Tu solicitud al proyecto '{solicitud.id_project.name}' ha sido rechazada.",
                'is_read': 0,
                'created_at': timezone.now(),
                'user_id': solicitud.id_user.id  
            }
            notification_serializer = NotificationSerializer(data=notification_data)
            
            if await sync_to_async(notification_serializer.is_valid)():
                await sync_to_async(notification_serializer.save)()
            else:
                return Response(notification_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
            return Response({"mensaje": "Solicitud negada exitosamente"}, status=status.HTTP_200_OK)
        
        except Solicitudes.DoesNotExist:
            return Response({"error": "Solicitud no encontrada"}, status=status.HTTP_404_NOT_FOUND)  

    @swagger_auto_schema(
    operation_summary="Obtener solicitudes del usuario",
    operation_description="Recupera todas las solicitudes (solicitudes) enviadas por el usuario autenticado.",
    responses={
        status.HTTP_200_OK: openapi.Response(
            'Solicitudes del usuario recuperadas con éxito',
            openapi.Schema(
                type=openapi.TYPE_ARRAY,
                items=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'id_solicitud': openapi.Schema(type=openapi.TYPE_INTEGER, description='ID de la solicitud'),
                        'id_project': openapi.Schema(type=openapi.TYPE_INTEGER, description='ID del proyecto'),
                        'status': openapi.Schema(type=openapi.TYPE_STRING, description='Estado actual de la solicitud'),
                        'created_at': openapi.Schema(type=openapi.TYPE_STRING, format='date-time', description='Fecha de creación de la solicitud'),
                        'name_project': openapi.Schema(type=openapi.TYPE_STRING, description='Nombre del proyecto'),
                        'name_user': openapi.Schema(type=openapi.TYPE_STRING, description='Nombre del usuario que aplicó'),
                        'message': openapi.Schema(type=openapi.TYPE_STRING, description='Mensaje de la solicitud')
                    }
                )
            )
        ),
        status.HTTP_404_NOT_FOUND: openapi.Response(
            'No se encontraron solicitudes para este usuario',
            openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'message': openapi.Schema(type=openapi.TYPE_STRING, description='Mensaje de error')
                }
            )
        ),
        status.HTTP_500_INTERNAL_SERVER_ERROR: openapi.Response(
            'Error interno del servidor',
            openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'error': openapi.Schema(type=openapi.TYPE_STRING, description='Descripción del error')
                }
            )
        )
    },
    tags=["Applications Management"]
    )
    @action(detail=False, methods=['GET'], url_path='applications_user', permission_classes=[IsAuthenticated])
    async def get_applications_user(self, request):
        user = request.user.id  
        
        try:
                solicitudes = await sync_to_async(list)(Solicitudes.objects.filter(id_user=user).order_by("-id_solicitud"))

                if not solicitudes:
                    return Response({"message": "No solicitudes found for this user"}, status=status.HTTP_404_NOT_FOUND)

                serializer = await sync_to_async(SolicitudSerializer)(solicitudes, many=True)
                return Response(serializer.data, status=status.HTTP_200_OK)

        except Exception as e:
                return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
    @swagger_auto_schema(
        operation_summary="Obtener solicitudes de un proyecto",
        operation_description="Recupera todas las solicitudes (solicitudes) para un proyecto específico.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['project_id'],
            properties={
                'project_id': openapi.Schema(type=openapi.TYPE_INTEGER, description="ID del proyecto")
            }
        ),
        responses={
            status.HTTP_200_OK: openapi.Response(
                'Solicitudes del proyecto recuperadas con éxito',
                openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Schema(
                        type=openapi.TYPE_OBJECT,
                        properties={
                            'id_solicitud': openapi.Schema(type=openapi.TYPE_INTEGER, description='ID de la solicitud'),
                            'id_user': openapi.Schema(type=openapi.TYPE_INTEGER, description='ID del usuario que aplicó'),
                            'status': openapi.Schema(type=openapi.TYPE_STRING, description='Estado actual de la solicitud'),
                            'created_at': openapi.Schema(type=openapi.TYPE_STRING, format='date-time', description='Fecha de creación de la solicitud'),
                            'name_user': openapi.Schema(type=openapi.TYPE_STRING, description='Nombre del usuario que aplicó'),
                            'message': openapi.Schema(type=openapi.TYPE_STRING, description='Mensaje de la solicitud'),
                            'photo': openapi.Schema(type=openapi.TYPE_STRING, description='Foto del usuario que aplicó')
                        }
                    )
                )
            ),
            status.HTTP_400_BAD_REQUEST: openapi.Response(
                'project_id es requerido',
                openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'error': openapi.Schema(type=openapi.TYPE_STRING, description='Descripción del error')
                    }
                )
            ),
            status.HTTP_404_NOT_FOUND: openapi.Response(
                'Proyecto no encontrado',
                openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'error': openapi.Schema(type=openapi.TYPE_STRING, description='Descripción del error')
                    }
                )
            ),
            status.HTTP_500_INTERNAL_SERVER_ERROR: openapi.Response(
                'Error interno del servidor',
                openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'error': openapi.Schema(type=openapi.TYPE_STRING, description='Descripción del error')
                    }
                )
            )
        },
        tags=["Applications Management"]
    )   
    @action(detail=False, methods=['POST'], url_path='applications_project', permission_classes=[IsAuthenticated])
    async def get_applications_project(self, request):
        project_id = request.data.get('project_id')

        if not project_id:
            return Response({"error": "project_id is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            project = await sync_to_async(Projects.objects.get)(id=project_id)
            
            solicitudes = await sync_to_async(list)(Solicitudes.objects.filter(id_project=project).order_by("-id_solicitud"))

            serializer = SolicitudSerializer(solicitudes, many=True)
            solicitudes_data = serializer.data

            for solicitud in solicitudes_data:
                user = await sync_to_async(Users.objects.get)(id=solicitud['id_user'])
                solicitud['photo'] = user.photo if user.photo else None

            return Response(solicitudes_data, status=status.HTTP_200_OK)

        except Projects.DoesNotExist:
            return Response({"error": "Project not found"}, status=status.HTTP_404_NOT_FOUND)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @swagger_auto_schema(
        operation_summary="Eliminar solicitud",
        operation_description="Permite a un usuario eliminar una solicitud específica si está en estado 'Rechazado' o 'Pendiente'.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['solicitud_id'],
            properties={
                'solicitud_id': openapi.Schema(type=openapi.TYPE_INTEGER, description='ID de la solicitud'),
            }
        ),
        responses={
            status.HTTP_204_NO_CONTENT: openapi.Response(
                'Solicitud eliminada exitosamente',
                openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'message': openapi.Schema(type=openapi.TYPE_STRING, description='Mensaje de éxito')
                    }
                )
            ),
            status.HTTP_400_BAD_REQUEST: openapi.Response('Error en los datos proporcionados o la solicitud no puede ser eliminada'),
            status.HTTP_404_NOT_FOUND: openapi.Response('Solicitud no encontrada o no pertenece al usuario'),
            status.HTTP_500_INTERNAL_SERVER_ERROR: openapi.Response('Error interno del servidor'),
        },
        tags=["Applications Management"]
    )
    @action(detail=False, methods=['DELETE'], url_path='delete_solicitud', permission_classes=[IsAuthenticated])
    async def delete_solicitud(self, request):
        solicitud_id = request.data.get('solicitud_id')
        user = request.user.id  

        if not solicitud_id:
            return Response({"error": "solicitud_id is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:

            solicitud = await sync_to_async(Solicitudes.objects.get)(id_solicitud=solicitud_id, id_user=user)


            if solicitud.status in ['Rechazado', 'Pendiente']:
                await sync_to_async(solicitud.delete)()
                return Response(status=status.HTTP_204_NO_CONTENT)
            else:
                return Response({"error": "Cannot delete a solicitud that has been accepted or is in another status"}, status=status.HTTP_400_BAD_REQUEST)

        except Solicitudes.DoesNotExist:
            return Response({"error": "Solicitud not found or does not belong to the user"}, status=status.HTTP_404_NOT_FOUND)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class NotificationsViewSet(ViewSet): #Notifiacions Management
    
    @swagger_auto_schema(
        operation_description="Obtener todas las notificaciones del usuario logueado",
        responses={
            status.HTTP_200_OK: openapi.Response('Lista de notificaciones obtenida exitosamente'),
            status.HTTP_401_UNAUTHORIZED: openapi.Response('Usuario no autorizado'),
        },
        tags=["Notifications Management"]
    )
    @action(detail=False, methods=['GET'], url_path='Getnotifications', permission_classes=[IsAuthenticated])
    async def Getnotifications(self, request):
        user = request.user
        
        try:
            # Obtener todas las notificaciones del usuario logueado
            notifications = await sync_to_async(list)(Notifications.objects.filter(user_id=user.id).order_by('-id'))

            # Serializar solo los mensajes de las notificaciones
            serializer = NotificationSerializerMS(notifications, many=True)

            return Response(serializer.data, status=status.HTTP_200_OK)
        except Notifications.DoesNotExist:
            return Response({"error": "No se encontraron notificaciones"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @swagger_auto_schema(
    operation_summary="Marcar notificaciones como leídas",
    operation_description="Permite a un usuario marcar todas sus notificaciones como leídas.",
    responses={
        status.HTTP_200_OK: openapi.Response(
            'Notificaciones marcadas como leídas',
            openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'message': openapi.Schema(type=openapi.TYPE_STRING, description='Mensaje de éxito')
                }
            )
        ),
        status.HTTP_500_INTERNAL_SERVER_ERROR: openapi.Response('Error interno del servidor'),
    },
    tags=["Notifications Management"])
    @action(detail=False, methods=['PUT'], url_path='isread_notifications', permission_classes=[IsAuthenticated])
    async def isread_notifications(self, request):
        user = request.user
        
        try:
            await sync_to_async(Notifications.objects.filter(user_id=user.id).update)(is_read=1)
            return Response({"message": "Notificaciones marcadas como leídas"}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
class CollaboratorsViewSet(ViewSet): #(Collaborators Management)
    
    @swagger_auto_schema(
        method='get',
        operation_summary="Retrieve Collaborated Projects",
        operation_description="Retrieve the list of projects the authenticated user has collaborated on.",
        responses={
            200: openapi.Response(
                description="Successful response with list of projects.",
                schema=ProjectSerializer(many=True)
            ),
            404: openapi.Response(description="No projects found for the collaborations.")
        },
        tags=["collaborators Management"]
    )
    @action(detail=False, methods=['GET'], url_path='view_project_usercollab', permission_classes=[IsAuthenticated])
    async def view_project_usercollab(self, request):

        user_instance = request.user.id  

        collaborations = await sync_to_async(list)(Collaborations.objects.filter(user=user_instance))


        if collaborations:
            
            project_ids = await sync_to_async(lambda: [collab.project_id for collab in collaborations])()
            projects = await sync_to_async(list)(Projects.objects.filter(id__in=project_ids))

            if projects:

                response_data = []
                for project in projects:
                    collaboratorsall = await sync_to_async(list)(Collaborations.objects.filter(project=project).select_related('user__authuser'))
                    
                    collaborators_info = await self.get_collaborators_info_proyect(collaboratorsall)

                    name_responsible = await self.get_responsible_name_proyect(project)

                    collaboration_count = await self.get_collaboration_count_proyect(project)
                    
                    responsible_user = await sync_to_async(Users.objects.get)(id=project.responsible_id)
                    responsible_photo = responsible_user.photo if responsible_user.photo else None

                    project_data = {
                        'id': project.id,
                        'name': project.name,
                        'description': project.description,
                        'start_date': project.start_date,
                        'end_date': project.end_date,
                        'status': project.status,
                        'project_type': project.project_type,
                        'priority': project.priority,
                        'responsible': project.responsible_id,  
                        'name_responsible': name_responsible,
                        'detailed_description': project.detailed_description,
                        'type_aplyuni': project.type_aplyuni,
                        'objectives': project.objectives,
                        'necessary_requirements': project.necessary_requirements,
                        'progress': project.progress,
                        'accepting_applications': project.accepting_applications,
                        'name_uniuser': project.name_uniuser,
                        'collaboration_count': collaboration_count,
                        'collaborators': collaborators_info,
                        'responsible_photo': responsible_photo,  
                    }
                    response_data.append(project_data)

                return Response(response_data, status=status.HTTP_200_OK)
            else:
                return Response({"message": "No se encontraron proyectos"}, status=status.HTTP_404_NOT_FOUND)

        else:
            return Response({"message": "No se encontraron colaboraciones."}, status=status.HTTP_404_NOT_FOUND)
        
    async def get_collaboration_count_proyect(self, project):
        return await sync_to_async(lambda: Collaborations.objects.filter(project=project).count())()

    async def get_collaborators_info_proyect(self, collaborators):
        collaborator_info = []
        for collab in collaborators:
            if collab.user and collab.user.authuser:
                photo = await sync_to_async(lambda: Users.objects.filter(id=collab.user.authuser.id).first())()
                user_info = {
                    "id": collab.user.id,
                    "photo" : photo.photo,
                    "name": f"{collab.user.authuser.first_name} {collab.user.authuser.last_name}"
                }
                collaborator_info.append(user_info)
        return collaborator_info

    async def get_responsible_name_proyect(self, obj):
        
        if obj.responsible_id: 
            authuser = await sync_to_async(User.objects.get)(id=obj.responsible_id)
            if authuser:
                return f"{authuser.first_name} {authuser.last_name}"    
           
    @swagger_auto_schema(
        method='delete',
        operation_summary="Delete Collaborator",
        operation_description="Delete a collaborator from a project.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'project_id': openapi.Schema(type=openapi.TYPE_INTEGER, description="ID of the project"),
                'user_id': openapi.Schema(type=openapi.TYPE_INTEGER, description="ID of the user to remove from project")
            },
            required=['project_id', 'user_id']
        ),
        responses={
            204: openapi.Response(description="Collaborator deleted successfully"),
            400: openapi.Response(description="Both project_id and user_id are required"),
            404: openapi.Response(description="Project/User/Collaboration not found"),
            500: openapi.Response(description="Internal server error")
        },
        tags=["collaborators Management"]
    )
    @action(detail=False, methods=['DELETE'], url_path='delete_collaborator', permission_classes=[IsAuthenticated])
    async def delete_collaborator(self, request):
        project_id = request.data.get('project_id')
        user_id = request.data.get('user_id')

        if not project_id or not user_id:
            return Response({"error": "Both project_id and user_id are required"}, status=status.HTTP_400_BAD_REQUEST)

        try:

            project = await sync_to_async(Projects.objects.get)(id=project_id)
            user = await sync_to_async(Users.objects.get)(id=user_id)


            collaboration = await sync_to_async(Collaborations.objects.filter)(project=project, user=user)
            collaboration_instance = await sync_to_async(collaboration.first)()
            if not collaboration_instance:
                return Response({"error": "Collaboration not found"}, status=status.HTTP_404_NOT_FOUND)

            await sync_to_async(collaboration_instance.delete)()


            solicitud = await sync_to_async(Solicitudes.objects.filter)(id_project=project, id_user=user)
            solicitud_instance = await sync_to_async(solicitud.first)()
            if solicitud_instance:
                await sync_to_async(solicitud_instance.delete)()

            notification_data = {
                'sender': request.user.id,  
                'message': f"Has sido eliminado como colaborador del proyecto '{project.name}'.",
                'is_read': 0,
                'created_at': timezone.now().strftime('%Y-%m-%d'),
                'user_id': user.id  
            }
            notification_serializer = NotificationSerializer(data=notification_data)

            if await sync_to_async(notification_serializer.is_valid)():
                await sync_to_async(notification_serializer.save)()
            else:
                return Response(notification_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

            return Response(status=status.HTTP_204_NO_CONTENT)

        except Projects.DoesNotExist:
            return Response({"error": "Project not found"}, status=status.HTTP_404_NOT_FOUND)
        except Users.DoesNotExist:
            return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class MetricsViewSet(ViewSet): #(Metrics Management)
    
    @swagger_auto_schema(
        operation_summary="Obtener métricas actuales del usuario",
        responses={
            200: openapi.Response('Métricas del usuario', 
                openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'Proyectos en Progreso': openapi.Schema(type=openapi.TYPE_INTEGER),
                        'Logros Desbloqueados': openapi.Schema(type=openapi.TYPE_INTEGER),
                        'Proyectos Finalizados': openapi.Schema(type=openapi.TYPE_INTEGER),
                        'Proyectos en los que eres Miembro': openapi.Schema(type=openapi.TYPE_INTEGER),
                        'Proyectos como Líder': openapi.Schema(type=openapi.TYPE_INTEGER),
                    }
                )
            ),
            404: "Usuario no encontrado",
        },
        tags=["Metrics Management"]
    )
    @action(detail=False, methods=['GET'], url_path='metrics', permission_classes=[IsAuthenticated])
    def metrics(self, request):
        user_id = request.user.id
        projects_in_progress = Projects.objects.filter(status='En progreso',responsible_id=user_id).count()
        
        unlocked_achievements = UserAchievements.objects.filter(user_id=user_id, unlocked=True).count()
        
        completed_projects = Projects.objects.filter(status='Completado',responsible_id=user_id).count()
        
        member_projects = Collaborations.objects.filter(user_id=user_id).values('project').distinct().count()

        leader_projects = Projects.objects.filter(responsible_id=user_id).count()

        metrics = {
            "proyectos_en_progreso": projects_in_progress,
            "logros_desbloqueados": unlocked_achievements,
            "proyectos_finalizados": completed_projects,
            "proyectos_en_los_que_eres_miembro": member_projects,
            "proyectos_como_líder": leader_projects,
        }

        return Response(metrics, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        method='post',
        operation_summary="Obtener métricas actuales del usuario",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'user_id': openapi.Schema(type=openapi.TYPE_INTEGER, description="ID del usuario"),
            },
            required=['user_id']
        ),
        responses={
            200: openapi.Response(
                'Métricas del usuario', 
                openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'Proyectos en Progreso': openapi.Schema(type=openapi.TYPE_INTEGER),
                        'Logros Desbloqueados': openapi.Schema(type=openapi.TYPE_INTEGER),
                        'Proyectos Finalizados': openapi.Schema(type=openapi.TYPE_INTEGER),
                        'Proyectos en los que eres Miembro': openapi.Schema(type=openapi.TYPE_INTEGER),
                        'Proyectos como Líder': openapi.Schema(type=openapi.TYPE_INTEGER),
                    }
                )
            ),
            404: "Usuario no encontrado",
        },
        tags=["Metrics Management"]
    )
    @action(detail=False, methods=['POST'], url_path='metrics_id', permission_classes=[IsAuthenticated])
    def metrics_id(self, request):
        user_id = request.data.get('user_id')
        
        if not user_id:
            return Response({"error": "user_id es requerido"}, status=status.HTTP_400_BAD_REQUEST)
        
        projects_in_progress = Projects.objects.filter(status='En progreso', responsible_id=user_id).count()
        
        unlocked_achievements = UserAchievements.objects.filter(user_id=user_id, unlocked=True).count()
        
        completed_projects = Projects.objects.filter(status='Completado', responsible_id=user_id).count()

        member_projects = Collaborations.objects.filter(user_id=user_id).values('project').distinct().count()

        leader_projects = Projects.objects.filter(responsible_id=user_id).count()
        
        photo =  Users.objects.filter(authuser_id=user_id).first()

        metrics = {
            "photo" : photo.photo,
            "proyectos_en_progreso": projects_in_progress,
            "logros_desbloqueados": unlocked_achievements,
            "proyectos_finalizados": completed_projects,
            "proyectos_en_los_que_eres_miembro": member_projects,
            "proyectos_como_líder": leader_projects,
        }

        return Response(metrics, status=status.HTTP_200_OK)
    