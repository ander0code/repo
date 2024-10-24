from adrf.viewsets import ViewSet
from django.contrib.auth.models import User
from django.utils import timezone
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from rest_framework.response import Response
from rest_framework import status
from .serializers import LoginSerializer, ProjectSerializerCreate,CustomUserSerializer, ProjectSerializerAll,SolicitudSerializer,ProjectSerializerID,ProjectUpdateSerializer,CollaboratorSerializer,ProjectSerializer, NotificationSerializer,ProfileSerializer, NotificationSerializerMS
from rest_framework.decorators import action
from rest_framework_simplejwt.tokens import RefreshToken
from django.core.mail import send_mail
from django.shortcuts import get_object_or_404
from usuario.models import Users,Projects,Solicitudes,Collaborations, Notifications
from rest_framework.permissions import AllowAny ,IsAuthenticated
import random

from asgiref.sync import sync_to_async

#acuerdate de que debes usar async y await

# Create your views here.
class LoginViewSet(ViewSet):
    
    @swagger_auto_schema(
        operation_description="User login",
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
                            'email': openapi.Schema(type=openapi.TYPE_STRING, description='Email of the user'),
                            'university': openapi.Schema(type=openapi.TYPE_STRING, description='University of the user'),
                            'career': openapi.Schema(type=openapi.TYPE_STRING, description='Career of the user'),
                            'cycle': openapi.Schema(type=openapi.TYPE_STRING, description='Cycle of the user'),
                            'biography': openapi.Schema(type=openapi.TYPE_STRING, description='Biography of the user'),
                            'photo': openapi.Schema(type=openapi.TYPE_STRING, description='Photo URL of the user'),
                            'achievements': openapi.Schema(type=openapi.TYPE_STRING, description='Achievements of the user'),
                            'first_name': openapi.Schema(type=openapi.TYPE_STRING, description='First name of the user'),
                            'last_name': openapi.Schema(type=openapi.TYPE_STRING, description='Last name of the user'),
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
        
        if not email or not password:
            return Response({"error": "Email and password are required"}, status=status.HTTP_400_BAD_REQUEST)
        
  
        # Crear el usuario en auth_user
        user = await sync_to_async(User.objects.create_user)(
            username=email, email=email, password=password,first_name=first_name, last_name=last_name 
            )

        # Ahora crea la entrada en la tabla Users
        users_data = {
            **request.data,  # Copia todos los datos del request
            'authuser': user.pk,  # Asigna el objeto User recién creado
            'created_at': timezone.now().strftime('%Y-%m-%d')  # Establece la fecha de creación
        }
        
        users_serializer = CustomUserSerializer(data=users_data)
        
        if await sync_to_async(users_serializer.is_valid)(raise_exception=False):
            await sync_to_async(users_serializer.save)()  # Guarda la instancia
            
            # Generar el token JWT
            refresh = RefreshToken.for_user(user)
            return Response({
                "refresh": str(refresh),
                "access": str(refresh.access_token),
                "user": users_serializer.data  # Retorna los datos del usuario
            }, status=status.HTTP_201_CREATED)
        
        return Response(users_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @swagger_auto_schema(
            operation_description="Request a password reset code",
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
            # Obtener el usuario basado en el correo electrónico
            user = await sync_to_async(User.objects.get)(email=email)

            # Generar un código de 6 dígitos
            reset_code = random.randint(100000, 999999)

            # Almacenar el código y la fecha en el modelo Users
            user_profile = await sync_to_async(Users.objects.get)(authuser=user) # Asegúrate de que tienes acceso al perfil del usuario
            user_profile.reset_code = reset_code
            user_profile.reset_code_created_at = timezone.now()
            await sync_to_async(user_profile.save)()

            # Enviar el correo electrónico con el código de restablecimiento
            send_mail(
                'Password Reset Code',
                f'Your password reset code is: {reset_code}',
                'noreply@yourdomain.com',  # Cambia esto por tu dirección de correo
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
            # Obtener el usuario por email desde auth_user
            user = await sync_to_async(User.objects.get)(email=email)
            
            # Obtener el perfil del usuario
            user_profile = await sync_to_async(Users.objects.get)(authuser=user)

            # Verificar si el código de restablecimiento es correcto
            if user_profile.reset_code == reset_code:
                # Cambiar la contraseña
                user.set_password(new_password)
                await sync_to_async(user.save)() 
                
                # Limpiar el código de restablecimiento
                user_profile.reset_code = None
                await sync_to_async(user_profile.save)()  # Guardar los cambios en el perfil
                
                return Response({"message": "Password successfully reset"}, status=status.HTTP_200_OK)
            else:
                return Response({"error": "Invalid reset code"}, status=status.HTTP_400_BAD_REQUEST)
        except User.DoesNotExist:
            return Response({"error": "Invalid email"}, status=status.HTTP_400_BAD_REQUEST)
        except Users.DoesNotExist:
            return Response({"error": "User profile not found"}, status=status.HTTP_400_BAD_REQUEST)
    
    @swagger_auto_schema(
        operation_description="Update user profile by ID",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['id'],
            properties={
                'id': openapi.Schema(type=openapi.TYPE_INTEGER, description='ID of the user to view'),
                'university': openapi.Schema(type=openapi.TYPE_STRING, description='University of the user'),
                'career': openapi.Schema(type=openapi.TYPE_STRING, description='Career of the user'),
                'cycle': openapi.Schema(type=openapi.TYPE_STRING, description='Cycle of the user'),
                'biography': openapi.Schema(type=openapi.TYPE_STRING, description='Biography of the user'),
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
                        'photo': openapi.Schema(type=openapi.TYPE_STRING, description='Photo URL of the user'),
                        'achievements': openapi.Schema(type=openapi.TYPE_STRING, description='Achievements of the user'),
                    }
                )
            ),
            status.HTTP_404_NOT_FOUND: openapi.Response('User not found'),
            status.HTTP_400_BAD_REQUEST: openapi.Response('Invalid input data'),
        },
        tags=["User Management"]
    )
    @action(detail=False, methods=['PUT'], url_path='update-profile',permission_classes=[IsAuthenticated])
    async def update_user_profile(self, request):

        user_id = request.data.get('id')
        try:
            # Obtener el perfil de usuario usando el ID (pk)
            user_profile = await sync_to_async(Users.objects.get)(pk=user_id)
        except Users.DoesNotExist:
            return Response({"error": "User profile not found"}, status=status.HTTP_404_NOT_FOUND)

        # Crea un serializador con los datos actuales del perfil y los nuevos datos enviados
        serializer = CustomUserSerializer(user_profile, data=request.data, partial=True)

        if await sync_to_async(serializer.is_valid)():
            await sync_to_async(serializer.save)()  # Guarda las actualizaciones
            return Response(serializer.data, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

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
            # Buscar al usuario en la tabla Users por su ID (pk)
            user_profile = await sync_to_async(Users.objects.get)(pk=user_id)
            
            # Obtener el usuario en la tabla auth_user
            auth_user = user_profile.authuser  # Asumiendo que 'authuser' es una FK a User

        except Users.DoesNotExist:
            return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)

        # Eliminar el perfil del usuario en la tabla personalizada Users
        await sync_to_async(user_profile.delete)()

        # Eliminar el usuario en la tabla auth_user
        await sync_to_async(auth_user.delete)()

        return Response(status=status.HTTP_204_NO_CONTENT)
 
class PerfilViewSet(ViewSet):
    
    @action(detail=False, methods=['POST'], url_path='profile', permission_classes=[IsAuthenticated])
    def profile_data(self, request):
        # Obtener la instancia del usuario autenticado
        user_id = request.user.id

        # Filtrar el perfil del usuario desde la tabla Users
        try:
            user_profile = Users.objects.get(authuser_id=user_id)
        except Users.DoesNotExist:
            return Response({"error": "User profile not found"}, status=404)

        # Serializar los datos del usuario
        serializer = ProfileSerializer(user_profile)
        return Response(serializer.data, status=200)

class PublicacionViewSet(ViewSet):
    
    # fUNCIONES GENERALES
    
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
                'project_type': openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Items(type=openapi.TYPE_STRING), description="project_type to apply"),
                'priority': openapi.Schema(type=openapi.TYPE_STRING, description='Priority level of the project'),
                'detailed_description': openapi.Schema(type=openapi.TYPE_STRING, description='Detailed description of the project'),
                'expected_benefits': openapi.Schema(type=openapi.TYPE_STRING, description='Expected benefits of the project'),
                'necessary_requirements': openapi.Schema(type=openapi.TYPE_STRING, description='Necessary requirements for the project'),
                'progress': openapi.Schema(type=openapi.TYPE_INTEGER, description='Progress percentage of the project'),
                'accepting_applications': openapi.Schema(type=openapi.TYPE_BOOLEAN, description='Accepting requests for collaboration'),
                'type_aplyuni': openapi.Schema(type=openapi.TYPE_STRING, description='type_aplyuni of the project'),  
            },
        ),
        responses={
            status.HTTP_201_CREATED: openapi.Response(
                'Project created successfully',
                openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'id': openapi.Schema(type=openapi.TYPE_INTEGER, description='ID of the created project'),
                        'name': openapi.Schema(type=openapi.TYPE_STRING, description='Name of the project'),
                        'description': openapi.Schema(type=openapi.TYPE_STRING, description='Description of the project'),
                        'start_date': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATETIME, description='Start date of the project'),
                        'end_date': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATETIME, description='End date of the project'),
                        'status': openapi.Schema(type=openapi.TYPE_STRING, description='Current status of the project'),
                        'project_type': openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            items=openapi.Items(type=openapi.TYPE_STRING),
                            description="List of project_type"
                        ),
                        'priority': openapi.Schema(type=openapi.TYPE_STRING, description='Priority level of the project'),
                        'responsible': openapi.Schema(type=openapi.TYPE_INTEGER, description='ID of the user responsible for the project'),
                        'detailed_description': openapi.Schema(type=openapi.TYPE_STRING, description='Detailed description of the project'),
                        'expected_benefits': openapi.Schema(type=openapi.TYPE_STRING, description='Expected benefits of the project'),
                        'necessary_requirements': openapi.Schema(type=openapi.TYPE_STRING, description='Necessary requirements for the project'),
                        'progress': openapi.Schema(type=openapi.TYPE_INTEGER, description='Progress percentage of the project'),
                        'accepting_applications': openapi.Schema(type=openapi.TYPE_BOOLEAN, description='Accepting requests for collaboration'),
                        'type_aplyuni': openapi.Schema(type=openapi.TYPE_STRING, description='type_aplyuni'),
                    },
                ),
            ),
            status.HTTP_400_BAD_REQUEST: openapi.Response('Invalid input data'),
        },
        tags=["CRUD Project Management"]
    )
    @action(detail=False, methods=['POST'], url_path='create_proyect', permission_classes=[IsAuthenticated])
    def create_project(self, request):
        
        responsible_user_id = request.user.id
        
        custom_user = Users.objects.get(authuser=responsible_user_id)
        
        # Rellenar automáticamente el campo 'responsible' con el ID del usuario autenticado
        project_data = {
            **request.data,
            'start_date': timezone.now().strftime('%Y-%m-%d'),  # Fecha de creación
            'name_uniuser': custom_user.university if custom_user.university else "",
            'responsible': responsible_user_id  # Asigna el usuario autenticado como responsable
        }
    
        # Serializa los datos
        project_serializer = ProjectSerializerCreate(data=project_data)
        
        if project_serializer.is_valid():
            project_serializer.save()  # Guarda el proyecto si los datos son válidos
            return Response(project_serializer.data, status=status.HTTP_201_CREATED)
        
        return Response(project_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @swagger_auto_schema(
        operation_description="Actualizar un proyecto específico pasando el ID y los datos del proyecto en el cuerpo de la solicitud",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'project_id': openapi.Schema(type=openapi.TYPE_INTEGER, description='ID del proyecto'),
                'name': openapi.Schema(type=openapi.TYPE_STRING, description='Nombre del proyecto'),
                'description': openapi.Schema(type=openapi.TYPE_STRING, description='Descripción del proyecto'),
                'start_date': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATE, description='Fecha de inicio'),
                'end_date': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATE, description='Fecha de finalización'),
                'status': openapi.Schema(type=openapi.TYPE_STRING, description='Estado del proyecto'),
                'project_type': openapi.Schema(type=openapi.TYPE_STRING, description='Tipo de proyecto'),
                'priority': openapi.Schema(type=openapi.TYPE_STRING, description='Prioridad del proyecto'),
                'responsible': openapi.Schema(type=openapi.TYPE_INTEGER, description='ID del responsable'),
                'detailed_description': openapi.Schema(type=openapi.TYPE_STRING, description='Descripción detallada'),
                'objectives': openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Items(type=openapi.TYPE_STRING), description='Objetivos'),
                'necessary_requirements': openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Items(type=openapi.TYPE_STRING), description='Requisitos necesarios'),
                'progress': openapi.Schema(type=openapi.TYPE_INTEGER, description='Progreso del proyecto'),
                'accepting_applications': openapi.Schema(type=openapi.TYPE_BOOLEAN, description='Si está aceptando aplicaciones'),
                'type_aplyuni': openapi.Schema(type=openapi.TYPE_STRING, description='Tipo de aplicación')
            },
            required=['project_id']  # El ID del proyecto es obligatorio
        ),
        responses={
            status.HTTP_200_OK: openapi.Response('Proyecto actualizado correctamente'),
            status.HTTP_404_NOT_FOUND: openapi.Response('Proyecto no encontrado'),
            status.HTTP_400_BAD_REQUEST: openapi.Response('Datos inválidos'),
        },
        tags=["Project Management"]
    )
    @action(detail=False, methods=['PUT'], url_path='update-project', permission_classes=[IsAuthenticated])
    def update_project(self, request):
        # Extraer el ID del proyecto del cuerpo de la solicitud
        project_id = request.data.get('project_id')
        if not project_id:
            return Response({"message": "ID del proyecto es requerido."}, status=status.HTTP_400_BAD_REQUEST)

        # Obtener la instancia del usuario autenticado
        user_instance = request.user.id

        # Buscar el proyecto por su ID y verificar que el responsable es el usuario autenticado
        project = get_object_or_404(Projects, id=project_id, responsible=user_instance)

        # Serializar los datos de actualización
        serializer = ProjectUpdateSerializer(project, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
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
        tags=["CRUD Project Management"]
    )
    @action(detail=False, methods=['delete'], url_path='delete_project', permission_classes=[IsAuthenticated])
    def delete_project(self, request):
        try:
            # Obtener el proyecto usando el ID (pk)
            project_id = request.data.get('id')
            project = Projects.objects.get(pk=project_id)
            project.delete()  # Elimina el proyecto
            return Response(status=status.HTTP_204_NO_CONTENT)  # Respuesta sin contenido
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
        tags=["CRUD Project Management"]
    )
    @action(detail=False, methods=['POST'], url_path='view_project_id', permission_classes=[IsAuthenticated])
    def view_project_id(self, request):
        project_id = request.data.get('id')

        if not project_id:
            return Response({"error": "Project ID is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Obtener el proyecto usando el ID
            project = Projects.objects.get(pk=project_id)
        except Projects.DoesNotExist:
            return Response({"error": "Project not found"}, status=status.HTTP_404_NOT_FOUND)

        # Serializa los datos del proyecto
        serializer = ProjectSerializerID(project, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    @swagger_auto_schema(
        operation_description="Retrieve all projects in ascending order by start date",
        responses={
            status.HTTP_200_OK: openapi.Response(
                description="List of projects in ascending order",
                schema=ProjectSerializerAll(many=True)
            ),
            status.HTTP_400_BAD_REQUEST: "Invalid request",
        },
        tags=["CRUD Project Management"]
    )
    @action(detail=False, methods=['GET'], url_path='view_project_all', permission_classes=[IsAuthenticated])
    def view_project_all(self, request):
        # Obtener todos los proyectos en orden ascendente por start_date
        projects = Projects.objects.all().order_by('start_date')
        
        # Serializar los proyectos
        serializer = ProjectSerializerAll(projects, many=True)
        
        return Response(serializer.data, status=status.HTTP_200_OK)
        
    #Postulaziones    
        
    @swagger_auto_schema(
        operation_description="Aplicar a un proyecto",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['project_id'],
            properties={
                'project_id': openapi.Schema(type=openapi.TYPE_INTEGER, description='ID del proyecto'),
                
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
                            }
                        ),
                        'notificación': openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                'user': openapi.Schema(type=openapi.TYPE_INTEGER, description='ID del usuario que recibe la notificación'),
                                'message': openapi.Schema(type=openapi.TYPE_STRING, description='Mensaje de la notificación'),
                                'is_read': openapi.Schema(type=openapi.TYPE_INTEGER, description='Estado de lectura de la notificación (0 o 1)'),
                                'created_at': openapi.Schema(type=openapi.TYPE_STRING, format='date-time', description='Fecha de creación de la notificación'),
                            }
                        )
                    }
                )
            ),
            status.HTTP_400_BAD_REQUEST: openapi.Response('Error en los datos proporcionados'),
            status.HTTP_404_NOT_FOUND: openapi.Response('Proyecto no encontrado'),
        },
        tags=["Notificacions Project Management"]
    )
    @action(detail=False, methods=['POST'], url_path='ApplyProject', permission_classes=[IsAuthenticated])
    def ApplyProject(self, request):
        project_id = request.data.get('project_id')
        user = request.user
        

        try:
            # Verificar si el proyecto acepta aplicaciones
            project = Projects.objects.get(id=project_id)
            if not project.accepting_applications:
                return Response({"error": "Este proyecto no está aceptando aplicaciones"}, status=status.HTTP_400_BAD_REQUEST)

            # Verificar si ya existe una solicitud para este proyecto y usuario
            existing_solicitud = Solicitudes.objects.filter(id_user=user.id, id_project=project_id).first()
            if existing_solicitud:
                return Response({"error": "Ya has aplicado a este proyecto."}, status=status.HTTP_400_BAD_REQUEST)

            # Obtener el ID del líder del proyecto (responsible)
            lider_id = project.responsible_id  # Suponiendo que el campo 'responsible' es un ForeignKey

            # Conectar con la tabla auth_user para obtener los datos del líder
            lider = User.objects.get(id=lider_id)  # auth_user se mapea al modelo 'User' de Django

            # Obtener el nombre completo del líder
            name_lider = f"{lider.first_name} {lider.last_name}"

            # Crear la solicitud
            solicitud_data = {
                'id_user': user.id,
                'name_lider': name_lider,
                'created_at': timezone.now().strftime('%Y-%m-%d'),
                'id_project': project.id,
                'status': 'Pendiente',
                'name_project': project.name,
                'name_user': f"{user.first_name} {user.last_name}",
            }

            solicitud_serializer = SolicitudSerializer(data=solicitud_data)

            if solicitud_serializer.is_valid():
                solicitud_serializer.save()
                print(user.id)
                
                user_proyect = Projects.objects.get(id=project_id)
                # Crear la notificación para el propietario del proyecto
                notification_data = {
                    'sender': user.id,  
                    'message': f"{user.first_name} {user.last_name} aplico al proyecto '{project.name}' ",
                    'is_read': 0,
                    'created_at': timezone.now(),
                    'user_id': lider_id
                }
                notification_serializer = NotificationSerializer(data=notification_data)
                
                if notification_serializer.is_valid():
                    notification_serializer.save()
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
        operation_description="Aceptar solicitud de un proyecto",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['id_solicitud'],
            properties={
                'id_solicitud': openapi.Schema(type=openapi.TYPE_INTEGER, description='ID de la solicitud'),
            }
        ),
        responses={
            status.HTTP_200_OK: openapi.Response('Solicitud aceptada exitosamente'),
            status.HTTP_400_BAD_REQUEST: openapi.Response('Error en los datos proporcionados'),
            status.HTTP_404_NOT_FOUND: openapi.Response('Solicitud no encontrada'),
        },
        tags=["Notificacions Project Management"]
    )
    @action(detail=False, methods=['POST'], url_path='AcceptProject',permission_classes=[IsAuthenticated])
    def AcceptProject(self, request):
        id_solicitud = request.data.get('id_solicitud')
        user = request.user

        try:
            solicitud = Solicitudes.objects.get(id_solicitud=id_solicitud)
            
            # Verificar si el usuario es el responsable del proyecto
            if solicitud.id_project.responsible.id != user.id:
                return Response({"error": "No tienes permiso para aceptar esta solicitud"}, status=status.HTTP_403_FORBIDDEN)

            # Cambiar el estado de la solicitud a 'Aceptada'
            solicitud.status = 'Aceptada'
            solicitud.save()

            # Crear una colaboración
            collaboration_data = {
                'user': solicitud.id_user.id,
                'project': solicitud.id_project.id,
                'status': 'Activa'
            }
            collaboration_serializer = CollaboratorSerializer(data=collaboration_data)
            
            if collaboration_serializer.is_valid():
                collaboration_serializer.save()
                # Crear la notificación para el usuario que aplicó al proyecto
                notification_data = {
                    'sender': user.id,  # El usuario que acepta la solicitud
                    'message': f"Tu solicitud al proyecto '{solicitud.id_project.name}' ha sido aceptada.",
                    'is_read': 0,
                    'created_at': timezone.now(),
                    'user_id': solicitud.id_user.id  # Usuario que aplicó al proyecto
                }
                notification_serializer = NotificationSerializer(data=notification_data)
                
                if notification_serializer.is_valid():
                    notification_serializer.save()
                else:
                    return Response(notification_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
                
                return Response({"mensaje": "Solicitud aceptada y colaboración creada exitosamente"}, status=status.HTTP_200_OK)
            else:
                return Response(collaboration_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        except Solicitudes.DoesNotExist:
            return Response({"error": "Solicitud no encontrada"}, status=status.HTTP_404_NOT_FOUND)

    @swagger_auto_schema(
        operation_description="Negar solicitud de un proyecto",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['solicitud_id'],
            properties={
                'solicitud_id': openapi.Schema(type=openapi.TYPE_INTEGER, description='ID de la solicitud'),
            }
        ),
        responses={
            status.HTTP_200_OK: openapi.Response('Solicitud negada exitosamente'),
            status.HTTP_400_BAD_REQUEST: openapi.Response('Error en los datos proporcionados'),
            status.HTTP_404_NOT_FOUND: openapi.Response('Solicitud no encontrada'),
        },
        tags=["Notificacions Project Management"]
    )
    @action(detail=False, methods=['POST'], url_path='Denyproject',permission_classes=[IsAuthenticated])
    def Denyproject(self, request):
        solicitud_id = request.data.get('solicitud_id')
        user = request.user

        try:
            solicitud = Solicitudes.objects.get(id_solicitud=solicitud_id)
            
            # Verificar si el usuario es el responsable del proyecto
            if solicitud.id_project.responsible.id != user.id:
                return Response({"error": "No tienes permiso para negar esta solicitud"}, status=status.HTTP_403_FORBIDDEN)

            # Cambiar el estado de la solicitud a 'Negada'
            solicitud.status = 'Rechazado'
            solicitud.save()
            
             # Crear la notificación para el usuario que aplicó al proyecto
            notification_data = {
                'sender': user.id,  # Usuario responsable del proyecto que rechaza la solicitud
                'message': f"Tu solicitud al proyecto '{solicitud.id_project.name}' ha sido rechazada.",
                'is_read': 0,
                'created_at': timezone.now(),
                'user_id': solicitud.id_user.id  # Usuario que aplicó al proyecto
            }
            notification_serializer = NotificationSerializer(data=notification_data)
            
            if notification_serializer.is_valid():
                notification_serializer.save()
            else:
                return Response(notification_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
            return Response({"mensaje": "Solicitud negada exitosamente"}, status=status.HTTP_200_OK)
        
        except Solicitudes.DoesNotExist:
            return Response({"error": "Solicitud no encontrada"}, status=status.HTTP_404_NOT_FOUND)  
    
    @swagger_auto_schema(
        operation_description="Obtener todas las notificaciones del usuario logueado",
        responses={
            status.HTTP_200_OK: openapi.Response('Lista de notificaciones obtenida exitosamente'),
            status.HTTP_401_UNAUTHORIZED: openapi.Response('Usuario no autorizado'),
        },
        tags=["Notificacions Project Management"]
    )
    @action(detail=False, methods=['GET'], url_path='GetNotifications', permission_classes=[IsAuthenticated])
    def GetNotifications(self, request):
        user = request.user
        
        try:
            # Obtener todas las notificaciones del usuario logueado
            notifications = Notifications.objects.filter(user_id=user.id).order_by('-id')

            # Serializar solo los mensajes de las notificaciones
            serializer = NotificationSerializerMS(notifications, many=True)

            return Response(serializer.data, status=status.HTTP_200_OK)
        except Notifications.DoesNotExist:
            return Response({"error": "No se encontraron notificaciones"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['GET'], url_path='solicitudes_user', permission_classes=[IsAuthenticated])
    def get_solicitudes_user(self, request):
        user = request.user.id  
        
        try:
            # Filtrar todas las solicitudes hechas por el usuario autenticado
            solicitudes = Solicitudes.objects.filter(id_user=user).order_by("-id_solicitud")

            # Verificar si el usuario tiene solicitudes
            if not solicitudes.exists():
                return Response({"message": "No solicitudes found for this user"}, status=status.HTTP_404_NOT_FOUND)

            # Serializar las solicitudes
            serializer = SolicitudSerializer(solicitudes, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
    @action(detail=False, methods=['POST'], url_path='solicitudes_project',permission_classes=[IsAuthenticated])
    def get_solicitudes_project(self, request):
        project_id = request.data.get('project_id')

        if not project_id:
            return Response({"error": "project_id is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Verificar si el proyecto existe
            project = Projects.objects.get(id=project_id)
            
            # Filtrar solicitudes por proyecto
            solicitudes = Solicitudes.objects.filter(id_project=project).order_by("-id_solicitud")
            
            # Serializar las solicitudes
            serializer = SolicitudSerializer(solicitudes, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)

        except Projects.DoesNotExist:
            return Response({"error": "Project not found"}, status=status.HTTP_404_NOT_FOUND)
        
    @action(detail=False, methods=['DELETE'], url_path='delete_solicitud', permission_classes=[IsAuthenticated])
    def delete_solicitud(self, request):
        solicitud_id = request.data.get('solicitud_id')
        user = request.user.id  

        if not solicitud_id:
            return Response({"error": "solicitud_id is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Verificar si la solicitud existe y pertenece al usuario autenticado
            solicitud = Solicitudes.objects.get(id_solicitud=solicitud_id, id_user=user)

            # Verificar si la solicitud ha sido rechazada o no
            if solicitud.status == 'Rechazado' or solicitud.status == 'Pendiente':
                # Si la solicitud está pendiente o ha sido rechazada, se permite eliminarla
                solicitud.delete()
                return Response({"message": "Solicitud deleted successfully"}, status=status.HTTP_204_NO_CONTENT)
            else:
                return Response({"error": "Cannot delete a solicitud that has been accepted or is in another status"}, status=status.HTTP_400_BAD_REQUEST)

        except Solicitudes.DoesNotExist:
            return Response({"error": "Solicitud not found or does not belong to the user"}, status=status.HTTP_404_NOT_FOUND)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    #--------------------------------------------

    @swagger_auto_schema(
        operation_description="Obtener proyectos creados por el usuario autenticado",
        responses={
            status.HTTP_200_OK: openapi.Response('Lista de proyectos creados por el usuario'),
            status.HTTP_404_NOT_FOUND: openapi.Response('No se encontraron proyectos'),
        },
        tags=["Project Management"]
    )
    @action(detail=False, methods=['GET'], url_path='my-projects', permission_classes=[IsAuthenticated])
    def view_project_usercreator(self, request):
        # Obtener la instancia del modelo Users asociada al usuario autenticado
        try:
            user_instance = request.user.id  # Ajusta esto si tu relación es diferente
        except Users.DoesNotExist:
            return Response({"message": "Usuario no encontrado."}, status=status.HTTP_404_NOT_FOUND)

        # Filtrar proyectos creados por el usuario
        projects = Projects.objects.filter(responsible=user_instance)

        if projects.exists():
            serializer = ProjectSerializer(projects, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
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
        tags=["Project Management"]
    )
    @action(detail=False, methods=['POST'], url_path='get-project-id', permission_classes=[IsAuthenticated])
    def get_project_id(self, request):
        project_id = request.data.get('id_project')
        if not project_id:
            return Response({"message": "ID del proyecto es requerido."}, status=status.HTTP_400_BAD_REQUEST)

        user_instance = request.user.id

        # Verificar el ID del usuario responsable
        project = Projects.objects.filter(id=project_id).first()
        
        if project is None:
            return Response({"message": "Proyecto no encontrado."}, status=status.HTTP_404_NOT_FOUND)

        if project.responsible.id != user_instance:
            return Response({"message": "El usuario no es responsable del proyecto."}, status=status.HTTP_403_FORBIDDEN)

        serializer = ProjectSerializer(project)
        
        return Response(serializer.data, status=status.HTTP_200_OK)
        
    @swagger_auto_schema(
        operation_description="Obtener proyectos en los que el usuario está colaborando",
        responses={
            status.HTTP_200_OK: openapi.Response('Lista de proyectos en los que el usuario colabora'),
            status.HTTP_404_NOT_FOUND: openapi.Response('No se encontraron proyectos'),
        },
        tags=["Project Management"]
    )
    @action(detail=False, methods=['GET'], url_path='my-collaborated-projects', permission_classes=[IsAuthenticated])
    def view_project_usercollab(self, request):
        # Obtener la instancia del usuario autenticado
        user_instance = request.user.id  # Ajusta esto si tu relación es diferente

        # Filtrar colaboraciones del usuario
        collaborations = Collaborations.objects.filter(user=user_instance)

        # Obtener los proyectos relacionados a las colaboraciones
        projects = Projects.objects.filter(id__in=collaborations.values_list('project', flat=True))

        if projects.exists():
            serializer = ProjectSerializer(projects, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            return Response({"message": "No se encontraron proyectos en los que colabora."}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=False, methods=['DELETE'], url_path='delete_collaborator', permission_classes=[IsAuthenticated])
    def delete_collaborator(self, request):
        project_id = request.data.get('project_id')
        user_id = request.data.get('user_id')

        if not project_id or not user_id:
            return Response({"error": "Both project_id and user_id are required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Verificar que el proyecto existe
            project = Projects.objects.get(id=project_id)

            # Verificar que el usuario existe
            user = Users.objects.get(id=user_id)

            # Verificar que la colaboración existe
            collaboration = Collaborations.objects.filter(project=project, user=user).first()

            if not collaboration:
                return Response({"error": "Collaboration not found"}, status=status.HTTP_404_NOT_FOUND)

            # Eliminar la colaboración
            collaboration.delete()

            return Response({"message": "Collaborator deleted successfully"}, status=status.HTTP_204_NO_CONTENT)

        except Projects.DoesNotExist:
            return Response({"error": "Project not found"}, status=status.HTTP_404_NOT_FOUND)
        except Users.DoesNotExist:
            return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

