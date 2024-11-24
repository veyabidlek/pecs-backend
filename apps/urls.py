from . import views
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from rest_framework import permissions
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from django.urls import re_path
from .views import *
from .login import *


schema_view = get_schema_view(
    openapi.Info(
        title="API Documentation",
        default_version='v1',
        description="Description of your API",
        terms_of_service="https://www.google.com/policies/terms/",
        contact=openapi.Contact(email="contact@example.com"),
        license=openapi.License(name="BSD License"),
    ),
    public=True,
    permission_classes=[permissions.AllowAny]
)


urlpatterns = [
    path('generate-code', GenerateCodeView.as_view(), name='generate_code'),
    path('api/recipient_profile_caregiver/', RecipientProfileCaregiverView.as_view(),
         name='recipient-profile-caregiver'),
    path('caregiver_profile', CaregiverProfileView.as_view(), name='caregiver_profile'),
    path('', IndexView.as_view(), name='home'),
    path('cr-profile', RecipientProfileView.as_view(), name='cr_profile'),
    path('cg-profile', CaregiverProfileView.as_view(), name='cg_profile'),
    path('login', LoginUserView.as_view(), name='login'),
    path('logout', LogoutUserView.as_view(), name='logout'),
    path('signup', SignupUserView.as_view(), name='signup'),
    path('recipient_profile', RecipientProfileView.as_view(), name='recipient_profile'),
    path('library', LibraryView.as_view(), name='library'),
    path('my_boards', BoardCollectionView.as_view(), name='my_boards'),
    path('folder/<int:id>', FolderImageView.as_view(), name='folder_image'),
    path('board/<int:board_id>', BoardDetailView.as_view(), name='board'),
    path('profile-page', ProfileView.as_view(), name='profile'),
    path('cr-profile-page', RecipientProfileView.as_view(), name='recipient_profile'),
    path("ajax/", PlaySoundView.as_view(), name='call_play_sound'),
    path('cr-cg', RecipientProfileCaregiverView.as_view(), name='cr_cg'),
    path('cg-cr', CaregiverRecipientView.as_view(), name='cg_cr'),
    path('verify-code', VerifyCodeView.as_view(), name='verify_code'),
    path('progress-tracking', ProgressView.as_view(), name='progress'),
    path('progress-bars', BarCharsView.as_view(), name='bars'),

    path('folder/', FolderCreateView.as_view(), name='folder-create'),


    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),  # For obtaining tokens
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),  # For refreshing tokens

    re_path(r'^playground/$', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    re_path(r'^docs/$', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc')

]

