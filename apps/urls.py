from . import views
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('', views.index_view, name = 'home'),
    path('cr-profile', views.recipient_profile_view, name = 'cr_profile'),
    path('cg-profile', views.caregiver_profile_view, name = 'cg_profile'),
    path('login', views.login_user_view, name = 'login'),
    path('logout', views.logout_user_view, name = 'logout'),
    path('signup', views.signup_user_view, name = 'signup'),
    path('recipient_profile', views.recipient_profile_view, name = 'recipient_profile'),
    path('caregiver_profile', views.caregiver_profile_view, name = 'caregiver_profile'),
    path('library', views.library_view, name = 'library'),
    path('my_boards', views.board_collection_view, name = 'my_boards'),
    path('category/<str:name>/<int:id>', views.category_image,name = 'category_image'),
    path('board/<int:id>', views.board_view,name = 'board'),
    # path('search', views.search, name = 'search'),
    # path('tab_content/<int:id>', views.tab_content, name = 'tab_content'),
    path("ajax/", views.call_play_sound, name='call_play_sound'),
    # path('settings', views.settings, name = 'settings'),
    # path('logout', views.logout_user, name='logout'),
    # path('signup', views.signup_user, name = 'signup'),
    # path('progress-tracking', views.progress, name = 'progress'),
]

urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)