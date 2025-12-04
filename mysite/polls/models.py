from django.db import models
from django.contrib.auth.models import User
from datetime import datetime
import re

# Create your models here.

class TeaShop(models.Model):
    """奶茶店模型"""
    place_id = models.CharField(max_length=200, unique=True, verbose_name='Google Place ID')
    name = models.CharField(max_length=200, verbose_name='店名')
    address = models.CharField(max_length=300, verbose_name='地址')
    phone = models.CharField(max_length=50, blank=True, null=True, verbose_name='電話')
    latitude = models.DecimalField(max_digits=10, decimal_places=7, verbose_name='緯度')
    longitude = models.DecimalField(max_digits=10, decimal_places=7, verbose_name='經度')
    rating = models.DecimalField(max_digits=2, decimal_places=1, verbose_name='評分')
    opening_hours = models.TextField(verbose_name='營業時間')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='建立時間')

    class Meta:
        verbose_name = '奶茶店'
        verbose_name_plural = '奶茶店列表'
        ordering = ['-rating', 'name']  # 按評分降冪、店名排序

    def __str__(self):
        return f"{self.name} ({self.rating}分)"

    def is_open_now(self):
        """判斷店家目前是否營業中"""
        if not self.opening_hours or '無資訊' in self.opening_hours:
            return None

        # 24小時營業
        if '24 小時營業' in self.opening_hours:
            return True

        # 取得目前時間
        now = datetime.now()
        weekday = now.weekday()  # 0=星期一, 6=星期日
        current_time = now.time()

        # 星期對照
        weekday_map = {
            0: '星期一',
            1: '星期二',
            2: '星期三',
            3: '星期四',
            4: '星期五',
            5: '星期六',
            6: '星期日'
        }

        today_name = weekday_map[weekday]

        # 解析營業時間字串
        # 格式: "星期一: 11:00 – 22:00 | 星期二: 12:00 – 22:00 | ..."
        try:
            days = self.opening_hours.split('|')
            for day in days:
                day = day.strip()
                if today_name in day:
                    # 檢查是否休息
                    if '休息' in day:
                        return False

                    # 提取所有時間範圍（支援多個時段，例如: "12:00 – 15:00, 17:30 – 21:30"）
                    time_pattern = r'(\d{1,2}:\d{2})\s*[–-]\s*(\d{1,2}:\d{2})'
                    matches = re.findall(time_pattern, day)

                    if matches:
                        # 檢查是否在任一時段內營業
                        for open_time_str, close_time_str in matches:
                            # 轉換為 time 物件
                            open_time = datetime.strptime(open_time_str, '%H:%M').time()
                            close_time = datetime.strptime(close_time_str, '%H:%M').time()

                            # 處理跨午夜的情況（例如: 23:00 - 02:00）
                            if close_time < open_time:
                                # 跨午夜：營業時間從 open_time 到 23:59:59 或從 00:00:00 到 close_time
                                if current_time >= open_time or current_time <= close_time:
                                    return True
                            else:
                                # 一般情況：在營業時間內
                                if open_time <= current_time <= close_time:
                                    return True

                        # 如果所有時段都不在營業時間內，則休息
                        return False

            return None
        except Exception:
            return None


class Drink(models.Model):
    """飲料品項模型"""
    MILK_TYPE_CHOICES = [
        ('creamer', '奶精'),
        ('fresh_milk', '鮮奶'),
    ]
    
    tea_shop = models.ForeignKey(TeaShop, on_delete=models.CASCADE, related_name='drinks', verbose_name='所屬店家')
    name = models.CharField(max_length=100, verbose_name='飲料名稱')
    description = models.TextField(blank=True, null=True, verbose_name='描述')
    milk_type = models.CharField(max_length=20, choices=MILK_TYPE_CHOICES, default='none', verbose_name='使用奶類')

    # 杯型與價格
    has_small = models.BooleanField(default=False, verbose_name='有小杯')
    price_small = models.DecimalField(max_digits=5, decimal_places=0, blank=True, null=True, verbose_name='小杯價格')

    has_medium = models.BooleanField(default=False, verbose_name='有中杯')
    price_medium = models.DecimalField(max_digits=5, decimal_places=0, blank=True, null=True, verbose_name='中杯價格')

    has_large = models.BooleanField(default=False, verbose_name='有大杯')
    price_large = models.DecimalField(max_digits=5, decimal_places=0, blank=True, null=True, verbose_name='大杯價格')

    created_at = models.DateTimeField(auto_now_add=True, verbose_name='建立時間')

    class Meta:
        verbose_name = '飲料品項'
        verbose_name_plural = '飲料品項列表'
        ordering = ['tea_shop', 'name']

    def __str__(self):
        return f"{self.tea_shop.name} - {self.name}"

    def get_price_range(self):
        """取得價格範圍"""
        prices = []
        if self.has_small and self.price_small:
            prices.append(int(self.price_small))
        if self.has_medium and self.price_medium:
            prices.append(int(self.price_medium))
        if self.has_large and self.price_large:
            prices.append(int(self.price_large))

        if not prices:
            return "價格未定"

        min_price = min(prices)
        max_price = max(prices)

        if min_price == max_price:
            return f"${min_price}"
        return f"${min_price}-${max_price}"


class Favorite(models.Model):
    """收藏模型 - 使用者收藏的店家或飲料"""
    FAVORITE_TYPE_CHOICES = [
        ('shop', '店家'),
        ('drink', '飲料'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='favorites', verbose_name='使用者')
    favorite_type = models.CharField(max_length=10, choices=FAVORITE_TYPE_CHOICES, verbose_name='收藏類型')
    tea_shop = models.ForeignKey(TeaShop, on_delete=models.CASCADE, blank=True, null=True, related_name='favorited_by', verbose_name='收藏的店家')
    drink = models.ForeignKey(Drink, on_delete=models.CASCADE, blank=True, null=True, related_name='favorited_by', verbose_name='收藏的飲料')
    notes = models.TextField(blank=True, null=True, verbose_name='備註')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='收藏時間')

    class Meta:
        verbose_name = '收藏'
        verbose_name_plural = '收藏列表'
        ordering = ['-created_at']
        unique_together = [['user', 'tea_shop', 'drink']]  # 避免重複收藏

    def __str__(self):
        if self.favorite_type == 'shop':
            return f"{self.user.username} 收藏 {self.tea_shop.name}"
        else:
            return f"{self.user.username} 收藏 {self.drink.name}"
