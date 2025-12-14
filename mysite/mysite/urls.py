"""
URL configuration for mysite project.
"""
from django.contrib import admin
from django.urls import path, include
from polls import views as polls_views


urlpatterns = [
    path('admin/', admin.site.urls),

    # 主頁和店家瀏覽
    path('', polls_views.home, name='home'),
    path('shops/', polls_views.shop_list, name='shop_list'),
    path('shops/<int:shop_id>/', polls_views.shop_detail, name='shop_detail'),
    path('drinks/', polls_views.recommended_drinks, name='recommended_drinks'),
    path('nearby/', polls_views.nearby_shops, name='nearby_shops'),
    path('search/', polls_views.search_drinks, name='search_drinks'),

    # 使用者認證
    path('register/', polls_views.register, name='register'),
    path('login/', polls_views.user_login, name='login'),
    path('logout/', polls_views.user_logout, name='logout'),

    # 收藏功能
    path('favorites/', polls_views.favorites_list, name='favorites_list'),
    path('favorites/add/', polls_views.add_favorite, name='add_favorite'),
    path('favorites/remove/', polls_views.remove_favorite, name='remove_favorite'),
    path('favorites/update-notes/', polls_views.update_favorite_notes, name='update_favorite_notes'),
    path('favorites/check/', polls_views.check_favorite, name='check_favorite'),
]
