from . import views
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static

from .views import *

urlpatterns = [
    path('api/recipient_profile_caregiver/', RecipientProfileCaregiverView.as_view(),
         name='recipient-profile-caregiver'),
    path('caregiver_profile', CaregiverProfileView.as_view(), name='caregiver_profile'),
    path('generate-code', GenerateCodeView.as_view(), name='generate_code'),
    path('', IndexView.as_view(), name='home'),
    path('cr-profile', RecipientProfileView.as_view(), name='cr_profile'),
    path('cg-profile', CaregiverProfileView.as_view(), name='cg_profile'),
    path('login', LoginUserView.as_view(), name='login'),
    path('logout', LogoutUserView.as_view(), name='logout'),
    path('signup', SignupUserView.as_view(), name='signup'),
    path('recipient_profile', RecipientProfileView.as_view(), name='recipient_profile'),
    path('library', LibraryView.as_view(), name='library'),
    path('my_boards', BoardCollectionView.as_view(), name='my_boards'),
    path('category/<str:name>/<int:id>', CategoryImageView.as_view(), name='category_image'),
    path('board/<int:id>', BoardCollectionView.as_view(), name='board'),
    path('board_category', BoardCategoryView.as_view(), name='board_category'),
    path('profile-page', ProfileView.as_view(), name='profile'),
    path('cr-profile-page', RecipientProfileView.as_view(), name='recipient_profile'),
    path("ajax/", PlaySoundView.as_view(), name='call_play_sound'),
    path('cr-cg', RecipientProfileCaregiverView.as_view(), name='cr_cg'),
    path('cg-cr', CaregiverRecipientView.as_view(), name='cg_cr'),
    path('verify-code', VerifyCodeView.as_view(), name='verify_code'),
    path('progress-tracking', ProgressView.as_view(), name='progress'),
    path('progress-bars', BarCharsView.as_view(), name='bars'),

    # path('', views.index_view, name='home'),
    # path('cr-profile', views.recipient_profile_view, name='cr_profile'),
    # path('cg-profile', views.caregiver_profile_view, name='cg_profile'),
    # path('login', views.login_user_view, name='login'),
    # path('logout', views.logout_user_view, name='logout'),
    # path('signup', views.signup_user_view, name='signup'),
    # path('recipient_profile', views.recipient_profile_view, name='recipient_profile'),
    # path('caregiver_profile', views.caregiver_profile_view, name='caregiver_profile'),
    # path('library', views.library_view, name='library'),
    # path('my_boards', views.board_collection_view, name='my_boards'),
    # path('category/<str:name>/<int:id>', views.category_image, name='category_image'),
    # path('board/<int:id>', views.board_view, name='board'),
    # path('board_category', views.board_category_view, name='board_category'),
    # path('profile-page', views.profile_view, name='profile'),
    # path('cr-profile-page', views.recipient_profile_view, name='recipient_profile'),
    # path('cg-profile-page', views.caregiver_profile_view, name='caregiver_profile'),
    # path('search', views.search, name = 'search'),
    # path('tab_content/<int:id>', views.tab_content, name = 'tab_content'),
    # path("ajax/", views.call_play_sound, name='call_play_sound'),
    # path('cr-cg', views.recipient_profile_caregiver_view, name='cr_cg'),
    # path('cg-cr', views.caregiver_recipient_view, name='cg_cr'),
    # path('generate-code', views.generate_code, name='generate_code'),
    # path('verify-code', views.verify_code, name='verify_code'),
    # path('settings', views.settings, name = 'settings'),
    # path('logout', views.logout_user, name='logout'),
    # path('signup', views.signup_user, name = 'signup'),
    # path('progress-tracking', views.progress, name='progress'),
    # path('progress-bars', views.bar_chars, name='bars'),
]

urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
