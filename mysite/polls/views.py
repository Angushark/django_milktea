from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Q
from .models import TeaShop, Drink, Favorite
from math import radians, sin, cos, sqrt, atan2
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm, PasswordResetForm
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.views import PasswordResetView, PasswordResetConfirmView


def home(request):
    """主首頁 - 簡化版本，只有搜尋欄和4個按鈕"""
    return render(request, 'polls/home.html')


def shop_list(request):
    """店家列表頁面 - 包含營業中篩選"""
    # 取得搜尋關鍵字
    search_query = request.GET.get('search', '')

    # 取得篩選參數
    rating_filter = request.GET.get('rating', '')
    open_now = request.GET.get('open_now', '')  # 'true' or ''
    sort_by = request.GET.get('sort', 'rating_desc')

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

    tea_shops = list(tea_shops)

    # 營業中篩選（Toggle 機制）
    if open_now == 'true':
        tea_shops = [shop for shop in tea_shops if shop.is_open_now() == True]

    # 排序（移除 name）
    if sort_by == 'rating_asc':
        tea_shops = sorted(tea_shops, key=lambda x: x.rating)
    else:  # rating_desc
        tea_shops = sorted(tea_shops, key=lambda x: x.rating, reverse=True)

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
    # 取得篩選參數
    rating_filter = request.GET.get('rating', '')
    milk_filter = request.GET.get('milk_type', '')
    price_filter = request.GET.get('price', '')
    tea_filter = request.GET.get('tea_type', '')
    topping_filter = request.GET.get('topping', '')
    sort_by = request.GET.get('sort', 'rating_desc')  # 預設評價由高到低

    # 基本查詢：建立基礎查詢集
    drinks = Drink.objects.select_related('tea_shop')

    # 評價篩選（店家評分）
    if rating_filter:
        try:
            min_rating = float(rating_filter)
            drinks = drinks.filter(tea_shop__rating__gte=min_rating)
        except ValueError:
            pass
    else:
        # 無篩選時的預設行為：顯示 4.0 星以上
        drinks = drinks.filter(tea_shop__rating__gte=4.0)

    # 奶類篩選
    if milk_filter:
        drinks = drinks.filter(milk_type=milk_filter)

    # 茶類篩選
    if tea_filter:
        drinks = drinks.filter(tea_type=tea_filter)

    # 配料篩選
    if topping_filter:
        drinks = drinks.filter(topping=topping_filter)

    # 轉換為列表以便價格篩選和排序
    drinks = list(drinks)

    # 價格篩選
    if price_filter == 'under_50':
        drinks = [d for d in drinks if has_price_in_range(d, 0, 50)]
    elif price_filter == '50_80':
        drinks = [d for d in drinks if has_price_in_range(d, 50, 80)]
    elif price_filter == 'over_80':
        drinks = [d for d in drinks if has_price_in_range(d, 80, float('inf'))]

    # 排序
    if sort_by == 'rating_desc' or sort_by == 'rating':
        drinks = sorted(drinks, key=lambda x: x.tea_shop.rating, reverse=True)
    elif sort_by == 'rating_asc':
        drinks = sorted(drinks, key=lambda x: x.tea_shop.rating)
    elif sort_by == 'price_asc':
        drinks = sorted(drinks, key=lambda x: get_min_price(x))
    elif sort_by == 'price_desc':
        drinks = sorted(drinks, key=lambda x: get_max_price(x), reverse=True)

    context = {
        'drinks': drinks[:50],  # 限制顯示數量
        'total_count': len(drinks),
        'rating_filter': rating_filter,
        'milk_filter': milk_filter,
        'price_filter': price_filter,
        'tea_filter': tea_filter,
        'topping_filter': topping_filter,
        'sort_by': sort_by,
    }

    return render(request, 'polls/recommended_drinks.html', context)


def nearby_shops(request):
    """附近店家頁面 - 根據使用者位置顯示"""
    # 取得使用者位置
    user_lat = request.GET.get('lat', '')
    user_lng = request.GET.get('lng', '')
    # 預設距離篩選為 1km (當有位置且未指定距離時)
    distance_filter = request.GET.get('distance', '1' if (user_lat and user_lng) else '')
    open_now = request.GET.get('open_now', '')  # Toggle
    sort_by = request.GET.get('sort', 'distance_asc')  # 預設距離由近到遠

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

            # 顯示距離統計
            if shops_with_distance:
                distances = [s.distance for s in shops_with_distance]
                print(f"距離範圍: 最近 {min(distances):.2f}km, 最遠 {max(distances):.2f}km")

            # 距離篩選（支援 0.5, 1, 3, 5, 8）
            if distance_filter:
                try:
                    max_distance = float(distance_filter)
                    before_count = len(shops_with_distance)
                    shops_with_distance = [s for s in shops_with_distance
                                          if s.distance <= max_distance]
                    after_count = len(shops_with_distance)
                    print(f"距離篩選: {max_distance}km, 篩選前: {before_count}家, 篩選後: {after_count}家")
                except ValueError:
                    print(f"距離篩選值無效: {distance_filter}")
                    pass

            # 營業中篩選
            if open_now == 'true':
                shops_with_distance = [s for s in shops_with_distance
                                      if s.is_open_now() == True]

            # 排序
            if sort_by == 'rating_desc' or sort_by == 'rating':
                tea_shops = sorted(shops_with_distance, key=lambda x: x.rating, reverse=True)
            elif sort_by == 'rating_asc':
                tea_shops = sorted(shops_with_distance, key=lambda x: x.rating)
            elif sort_by == 'distance_desc':
                tea_shops = sorted(shops_with_distance, key=lambda x: x.distance, reverse=True)
            else:  # distance_asc or distance
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
        'open_now': open_now,
        'sort_by': sort_by,
    }

    return render(request, 'polls/nearby_shops.html', context)


def shop_detail(request, shop_id):
    """店家詳細頁面 - 顯示店家資訊和飲料品項"""
    from django.shortcuts import get_object_or_404

    shop = get_object_or_404(TeaShop, id=shop_id)

    # 取得篩選參數
    milk_filter = request.GET.get('milk_type', '')
    price_filter = request.GET.get('price', '')
    tea_filter = request.GET.get('tea_type', '')
    topping_filter = request.GET.get('topping', '')
    sort_by = request.GET.get('sort', 'name')

    # 取得該店家的所有飲料
    drinks = Drink.objects.filter(tea_shop=shop)

    # 奶類篩選（只保留 fresh_milk 和 creamer）
    if milk_filter in ['fresh_milk', 'creamer']:
        drinks = drinks.filter(milk_type=milk_filter)

    # 茶類篩選
    if tea_filter:
        drinks = drinks.filter(tea_type=tea_filter)

    # 配料篩選
    if topping_filter:
        drinks = drinks.filter(topping=topping_filter)

    # 轉換為列表以便價格篩選和排序
    drinks = list(drinks)

    # 價格篩選
    if price_filter == 'under_50':
        drinks = [d for d in drinks if has_price_in_range(d, 0, 50)]
    elif price_filter == '50_80':
        drinks = [d for d in drinks if has_price_in_range(d, 50, 80)]
    elif price_filter == 'over_80':
        drinks = [d for d in drinks if has_price_in_range(d, 80, float('inf'))]

    # 排序（移除 name）
    if sort_by == 'price_asc':
        drinks = sorted(drinks, key=lambda x: get_min_price(x))
    elif sort_by == 'price_desc':
        drinks = sorted(drinks, key=lambda x: get_max_price(x), reverse=True)
    else:
        drinks = sorted(drinks, key=lambda x: x.name)

    context = {
        'shop': shop,
        'drinks': drinks,
        'total_drinks': len(drinks),
        'milk_filter': milk_filter,
        'price_filter': price_filter,
        'tea_filter': tea_filter,
        'topping_filter': topping_filter,
        'sort_by': sort_by,
    }

    return render(request, 'polls/shop_detail.html', context)


def get_min_price(drink):
    """取得飲料的最低價格"""
    prices = []
    if drink.has_medium and drink.price_medium:
        prices.append(float(drink.price_medium))
    if drink.has_large and drink.price_large:
        prices.append(float(drink.price_large))
    return min(prices) if prices else 0


def get_max_price(drink):
    """取得飲料的最高價格"""
    prices = []
    if drink.has_medium and drink.price_medium:
        prices.append(float(drink.price_medium))
    if drink.has_large and drink.price_large:
        prices.append(float(drink.price_large))
    return max(prices) if prices else 0


def has_price_in_range(drink, min_price, max_price):
    """檢查飲料是否有任何杯型的價格在指定範圍內"""
    prices = []
    if drink.has_medium and drink.price_medium:
        prices.append(float(drink.price_medium))
    if drink.has_large and drink.price_large:
        prices.append(float(drink.price_large))

    return any(min_price <= p < max_price for p in prices)


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


# ===== 使用者認證相關 =====

def register(request):
    """使用者註冊"""
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, '註冊成功！歡迎加入奶茶尋。')
            return redirect('home')
    else:
        form = UserCreationForm()
    return render(request, 'polls/register.html', {'form': form})


def user_login(request):
    """使用者登入"""
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, f'歡迎回來，{username}！')
                next_url = request.GET.get('next', 'home')
                return redirect(next_url)
    else:
        form = AuthenticationForm()
    return render(request, 'polls/login.html', {'form': form})


def user_logout(request):
    """使用者登出"""
    logout(request)
    messages.info(request, '您已成功登出。')
    return redirect('home')


# ===== 收藏功能相關 =====

@login_required
def favorites_list(request):
    """個人收藏清單頁面"""
    # 取得篩選類型
    filter_type = request.GET.get('type', 'all')  # all, shop, drink

    # 取得使用者的所有收藏
    favorites = Favorite.objects.filter(user=request.user)

    # 根據類型篩選
    if filter_type == 'shop':
        favorites = favorites.filter(favorite_type='shop')
    elif filter_type == 'drink':
        favorites = favorites.filter(favorite_type='drink')

    context = {
        'favorites': favorites,
        'filter_type': filter_type,
        'total_count': favorites.count(),
    }

    return render(request, 'polls/favorites.html', context)


@login_required
@require_POST
def add_favorite(request):
    """新增收藏（AJAX）"""
    favorite_type = request.POST.get('type')  # shop 或 drink
    item_id = request.POST.get('id')

    try:
        if favorite_type == 'shop':
            shop = get_object_or_404(TeaShop, id=item_id)
            favorite, created = Favorite.objects.get_or_create(
                user=request.user,
                favorite_type='shop',
                tea_shop=shop,
                drink=None
            )
        elif favorite_type == 'drink':
            drink = get_object_or_404(Drink, id=item_id)
            favorite, created = Favorite.objects.get_or_create(
                user=request.user,
                favorite_type='drink',
                drink=drink,
                tea_shop=None
            )
        else:
            return JsonResponse({'success': False, 'message': '無效的類型'}, status=400)

        if created:
            return JsonResponse({'success': True, 'message': '已加入收藏'})
        else:
            return JsonResponse({'success': False, 'message': '已經在收藏清單中'})

    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)


@login_required
@require_POST
def remove_favorite(request):
    """移除收藏（AJAX）"""
    favorite_id = request.POST.get('id')

    try:
        favorite = get_object_or_404(Favorite, id=favorite_id, user=request.user)
        favorite.delete()
        return JsonResponse({'success': True, 'message': '已移除收藏'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)


@login_required
@require_POST
def update_favorite_notes(request):
    """更新收藏備註（AJAX）"""
    favorite_id = request.POST.get('id')
    notes = request.POST.get('notes', '')

    try:
        favorite = get_object_or_404(Favorite, id=favorite_id, user=request.user)
        favorite.notes = notes
        favorite.save()
        return JsonResponse({'success': True, 'message': '備註已更新'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)


@login_required
def check_favorite(request):
    """檢查某項目是否已收藏（AJAX）"""
    favorite_type = request.GET.get('type')
    item_id = request.GET.get('id')

    try:
        if favorite_type == 'shop':
            exists = Favorite.objects.filter(
                user=request.user,
                favorite_type='shop',
                tea_shop_id=item_id
            ).exists()
        elif favorite_type == 'drink':
            exists = Favorite.objects.filter(
                user=request.user,
                favorite_type='drink',
                drink_id=item_id
            ).exists()
        else:
            return JsonResponse({'favorited': False})

        return JsonResponse({'favorited': exists})
    except Exception:
        return JsonResponse({'favorited': False})


def search_drinks(request):
    """智能飲料搜尋 - 支援模糊匹配、茶類、奶類等多種搜尋方式"""
    search_query = request.GET.get('search', '').strip()

    if not search_query:
        return redirect('home')

    # 開始建立查詢
    all_drinks = Drink.objects.select_related('tea_shop').all()

    # === 階段 1: 精確匹配（優先級最高） ===
    # 直接匹配飲料名稱、描述或店家名稱
    exact_matches = all_drinks.filter(
        Q(name__icontains=search_query) |
        Q(description__icontains=search_query) |
        Q(tea_shop__name__icontains=search_query)
    ).distinct()

    # 如果精確匹配有結果，優先返回這些結果
    if exact_matches.exists():
        drinks = list(exact_matches)
    else:
        # === 階段 2: 智能拆解匹配（當精確匹配無結果時） ===
        query_conditions = Q()

        # 常見飲料組合關鍵字（完整詞優先）
        drink_combinations = {
            '鮮奶茶': Q(name__icontains='鮮奶') & Q(name__icontains='茶'),
            '奶精茶': Q(name__icontains='奶精') & Q(name__icontains='茶'),
            '珍珠奶茶': Q(name__icontains='珍珠') & Q(name__icontains='奶茶'),
            '珍奶': Q(name__icontains='珍珠') | Q(name__icontains='奶茶'),
            '奶綠': Q(name__icontains='奶綠') | (Q(name__icontains='綠茶') & Q(milk_type__isnull=False)),
            '紅茶拿鐵': Q(name__icontains='紅茶') & Q(name__icontains='拿鐵'),
            '綠茶拿鐵': Q(name__icontains='綠茶') & Q(name__icontains='拿鐵'),
            '烏龍拿鐵': Q(name__icontains='烏龍') & Q(name__icontains='拿鐵'),
            '抹茶拿鐵': Q(name__icontains='抹茶') & Q(name__icontains='拿鐵'),
        }

        # 檢查是否匹配組合關鍵字
        matched_combination = False
        for combo_keyword, combo_query in drink_combinations.items():
            if combo_keyword in search_query:
                query_conditions |= combo_query
                matched_combination = True
                break

        # 如果沒有匹配到組合關鍵字，則進行單一屬性匹配
        if not matched_combination:
            # 茶類搜尋（僅當搜尋詞是純茶類時）
            tea_type_mapping = {
                '紅茶': 'black_tea',
                '綠茶': 'green_tea',
                '烏龍茶': 'oolong_tea',
                '烏龍': 'oolong_tea',
                '青茶': 'blue_tea',
                '抹茶': 'matcha',
                '鐵觀音': 'tieguanyin',
                '麥茶': 'barley_tea',
                '四季春': 'season',
                '茉莉花茶': 'jasmine',
                '茉莉': 'jasmine',
                '普洱茶': 'pu_erh',
                '普洱': 'pu_erh',
            }

            tea_matched = False
            for tea_name, tea_code in tea_type_mapping.items():
                # 只有當搜尋詞完全是茶類名稱時才用茶類篩選
                if search_query == tea_name or (tea_name in search_query and len(search_query) <= len(tea_name) + 2):
                    query_conditions |= Q(tea_type=tea_code)
                    tea_matched = True
                    break

            # 奶類搜尋（僅當搜尋詞是純奶類時）
            if search_query in ['鮮奶', '牛奶'] or (search_query.endswith('鮮奶') and len(search_query) <= 6):
                query_conditions |= Q(milk_type='fresh_milk')
            elif search_query == '奶精' or (search_query.endswith('奶精') and len(search_query) <= 6):
                query_conditions |= Q(milk_type='creamer')

            # 配料搜尋
            if search_query in ['珍珠', '波霸', '配料'] or search_query.startswith('珍珠'):
                query_conditions |= Q(topping='yes')

            # 如果以上都沒匹配，嘗試部分匹配飲料名稱
            if not tea_matched and not query_conditions:
                # 拆解搜尋詞中的關鍵字
                keywords_to_try = []
                if '拿鐵' in search_query:
                    keywords_to_try.append('拿鐵')
                if '奶茶' in search_query and search_query != '奶茶':
                    keywords_to_try.append('奶茶')

                for keyword in keywords_to_try:
                    query_conditions |= Q(name__icontains=keyword)

        # 應用查詢條件
        if query_conditions:
            drinks = list(all_drinks.filter(query_conditions).distinct())
        else:
            drinks = []

    # === 階段 3: 智能排序 ===
    def get_relevance_score(drink):
        """計算相關性分數，分數越高越相關"""
        score = 0
        drink_name_lower = drink.name.lower()
        query_lower = search_query.lower()

        # 1. 完全匹配（最高分）
        if query_lower == drink_name_lower:
            score += 1000

        # 2. 名稱開頭匹配
        if drink_name_lower.startswith(query_lower):
            score += 500

        # 3. 名稱包含完整關鍵字
        if query_lower in drink_name_lower:
            score += 300

        # 4. 店家評分加成
        score += float(drink.tea_shop.rating) * 10

        return score

    # 按相關性和店家評分排序
    drinks = sorted(drinks, key=get_relevance_score, reverse=True)

    # 限制結果數量（前 100 項）
    drinks = drinks[:100]

    context = {
        'drinks': drinks,
        'total_count': len(drinks),
        'search_query': search_query,
    }

    return render(request, 'polls/search_results.html', context)
