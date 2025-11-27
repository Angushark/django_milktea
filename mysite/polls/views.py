from django.shortcuts import render
from django.db.models import Q
from .models import TeaShop, Drink
from math import radians, sin, cos, sqrt, atan2


def home(request):
    """主首頁 - 簡化版本，只有搜尋欄和4個按鈕"""
    return render(request, 'polls/home.html')


def shop_list(request):
    """店家列表頁面 - 包含營業中篩選"""
    # 取得搜尋關鍵字
    search_query = request.GET.get('search', '')

    # 取得篩選參數
    rating_filter = request.GET.get('rating', '')
    open_now = request.GET.get('open_now', '')
    sort_by = request.GET.get('sort', '-rating')

    # 基本查詢
    tea_shops = TeaShop.objects.all()

    # 搜尋功能
    if search_query:
        tea_shops = tea_shops.filter(
            Q(name__icontains=search_query) |
            Q(address__icontains=search_query)
        )

    # 評分篩選
    if rating_filter:
        try:
            min_rating = float(rating_filter)
            tea_shops = tea_shops.filter(rating__gte=min_rating)
        except ValueError:
            pass

    # 營業中篩選
    if open_now:
        tea_shops = [shop for shop in tea_shops if shop.is_open_now() == True]
    else:
        tea_shops = list(tea_shops)

    # 排序
    if sort_by == 'rating_asc':
        tea_shops = sorted(tea_shops, key=lambda x: x.rating)
    elif sort_by == 'rating_desc' or sort_by == '-rating':
        tea_shops = sorted(tea_shops, key=lambda x: x.rating, reverse=True)
    elif sort_by == 'name':
        tea_shops = sorted(tea_shops, key=lambda x: x.name)

    context = {
        'tea_shops': tea_shops,
        'total_count': len(tea_shops),
        'search_query': search_query,
        'rating_filter': rating_filter,
        'open_now': open_now,
        'sort_by': sort_by,
    }

    return render(request, 'polls/shop_list.html', context)


def recommended_drinks(request):
    """推薦品項頁面"""
    drinks = Drink.objects.filter(
        tea_shop__rating__gte=4.0
    ).select_related('tea_shop').order_by('-tea_shop__rating')[:20]

    context = {
        'drinks': drinks,
        'total_count': drinks.count(),
    }

    return render(request, 'polls/recommended_drinks.html', context)


def nearby_shops(request):
    """附近店家頁面 - 根據使用者位置顯示"""
    # 取得使用者位置
    user_lat = request.GET.get('lat', '')
    user_lng = request.GET.get('lng', '')
    distance_filter = request.GET.get('distance', '')

    tea_shops = TeaShop.objects.all()

    # 如果有使用者位置，計算距離
    if user_lat and user_lng:
        try:
            user_lat = float(user_lat)
            user_lng = float(user_lng)

            # 計算每家店的距離
            shops_with_distance = []
            for shop in tea_shops:
                distance = calculate_distance(
                    user_lat, user_lng,
                    float(shop.latitude), float(shop.longitude)
                )
                shop.distance = distance
                shops_with_distance.append(shop)

            # 距離篩選
            if distance_filter:
                try:
                    max_distance = float(distance_filter)
                    shops_with_distance = [s for s in shops_with_distance if s.distance <= max_distance]
                except ValueError:
                    pass

            # 按距離排序
            tea_shops = sorted(shops_with_distance, key=lambda x: x.distance)

        except (ValueError, TypeError):
            tea_shops = list(tea_shops.order_by('-rating'))
    else:
        # 如果沒有位置，顯示高評分店家
        tea_shops = list(tea_shops.order_by('-rating')[:20])

    context = {
        'tea_shops': tea_shops,
        'total_count': len(tea_shops),
        'user_lat': user_lat,
        'user_lng': user_lng,
        'distance_filter': distance_filter,
    }

    return render(request, 'polls/nearby_shops.html', context)


def shop_detail(request, shop_id):
    """店家詳細頁面 - 顯示店家資訊和飲料品項"""
    from django.shortcuts import get_object_or_404

    shop = get_object_or_404(TeaShop, id=shop_id)

    # 取得篩選參數
    milk_filter = request.GET.get('milk_type', '')
    sort_by = request.GET.get('sort', 'name')

    # 取得該店家的所有飲料
    drinks = Drink.objects.filter(tea_shop=shop)

    # 奶類篩選
    if milk_filter:
        drinks = drinks.filter(milk_type=milk_filter)

    # 轉換為列表以便排序
    drinks = list(drinks)

    # 排序
    if sort_by == 'price_asc':
        # 按最低價格排序（升冪）
        drinks = sorted(drinks, key=lambda x: get_min_price(x))
    elif sort_by == 'price_desc':
        # 按最高價格排序（降冪）
        drinks = sorted(drinks, key=lambda x: get_max_price(x), reverse=True)
    elif sort_by == 'name':
        # 按名稱排序
        drinks = sorted(drinks, key=lambda x: x.name)

    context = {
        'shop': shop,
        'drinks': drinks,
        'total_drinks': len(drinks),
        'milk_filter': milk_filter,
        'sort_by': sort_by,
    }

    return render(request, 'polls/shop_detail.html', context)


def get_min_price(drink):
    """取得飲料的最低價格"""
    prices = []
    if drink.has_small and drink.price_small:
        prices.append(float(drink.price_small))
    if drink.has_medium and drink.price_medium:
        prices.append(float(drink.price_medium))
    if drink.has_large and drink.price_large:
        prices.append(float(drink.price_large))
    return min(prices) if prices else 0


def get_max_price(drink):
    """取得飲料的最高價格"""
    prices = []
    if drink.has_small and drink.price_small:
        prices.append(float(drink.price_small))
    if drink.has_medium and drink.price_medium:
        prices.append(float(drink.price_medium))
    if drink.has_large and drink.price_large:
        prices.append(float(drink.price_large))
    return max(prices) if prices else 0


def calculate_distance(lat1, lon1, lat2, lon2):
    """使用 Haversine 公式計算兩點間的距離（公里）"""
    R = 6371  # 地球半徑（公里）

    lat1_rad = radians(lat1)
    lat2_rad = radians(lat2)
    delta_lat = radians(lat2 - lat1)
    delta_lon = radians(lon2 - lon1)

    a = sin(delta_lat / 2) ** 2 + cos(lat1_rad) * cos(lat2_rad) * sin(delta_lon / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))

    distance = R * c
    return distance


def index(request):
    """主首頁 - v2 完整版本（保留以供參考）"""

    # 取得搜尋關鍵字
    search_query = request.GET.get('search', '')

    # 取得篩選參數
    rating_filter = request.GET.get('rating', '')  # 評分篩選
    sort_by = request.GET.get('sort', '-rating')  # 排序方式，預設按評分降冪

    # 基本查詢
    tea_shops = TeaShop.objects.all()

    # 搜尋功能
    if search_query:
        tea_shops = tea_shops.filter(
            Q(name__icontains=search_query) |
            Q(address__icontains=search_query)
        )

    # 評分篩選
    if rating_filter:
        try:
            min_rating = float(rating_filter)
            tea_shops = tea_shops.filter(rating__gte=min_rating)
        except ValueError:
            pass

    # 排序
    if sort_by == 'rating_asc':
        tea_shops = tea_shops.order_by('rating')
    elif sort_by == 'rating_desc' or sort_by == '-rating':
        tea_shops = tea_shops.order_by('-rating')
    elif sort_by == 'name':
        tea_shops = tea_shops.order_by('name')

    # 推薦品項 - 取得有飲料的店家中評分最高的飲料
    recommended_drinks = Drink.objects.filter(
        tea_shop__rating__gte=4.0
    ).select_related('tea_shop').order_by('-tea_shop__rating')[:6]

    # 附近店家 - 先取得評分最高的幾家
    nearby_shops = TeaShop.objects.all().order_by('-rating')[:6]

    context = {
        'tea_shops': tea_shops,
        'total_count': tea_shops.count(),
        'search_query': search_query,
        'rating_filter': rating_filter,
        'sort_by': sort_by,
        'recommended_drinks': recommended_drinks,
        'nearby_shops': nearby_shops,
    }

    return render(request, 'polls/index.html', context)
