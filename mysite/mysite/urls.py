"""
URL configuration for mysite project.
"""
from django.contrib import admin
from django.urls import path
from polls import views as polls_views


urlpatterns = [
    path('admin/', admin.site.urls),
    path('', polls_views.home, name='home'),  # 主首頁（簡化版）
    path('shops/', polls_views.shop_list, name='shop_list'),  # 店家列表
    path('shops/<int:shop_id>/', polls_views.shop_detail, name='shop_detail'),  # 店家詳細頁面
    path('drinks/', polls_views.recommended_drinks, name='recommended_drinks'),  # 推薦品項
    path('nearby/', polls_views.nearby_shops, name='nearby_shops'),  # 附近店家
]
