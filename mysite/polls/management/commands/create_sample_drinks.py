from django.core.management.base import BaseCommand
from polls.models import TeaShop, Drink


class Command(BaseCommand):
    help = '建立測試飲料資料'

    def handle(self, *args, **kwargs):
        # 取得前幾家店
        shops = TeaShop.objects.all()[:10]

        if not shops:
            self.stdout.write(self.style.ERROR('沒有店家資料，請先匯入店家'))
            return

        # 常見飲料品項
        common_drinks = [
            {'name': '珍珠奶茶', 'milk_type': 'both', 'description': '經典珍珠奶茶'},
            {'name': '黑糖珍珠鮮奶', 'milk_type': 'fresh_milk', 'description': '黑糖珍珠搭配鮮奶'},
            {'name': '冬瓜檸檬', 'milk_type': 'none', 'description': '清爽冬瓜配檸檬'},
            {'name': '波霸奶茶', 'milk_type': 'creamer', 'description': '大顆波霸奶茶'},
            {'name': '鐵觀音拿鐵', 'milk_type': 'fresh_milk', 'description': '鐵觀音茶拿鐵'},
            {'name': '百香綠茶', 'milk_type': 'none', 'description': '百香果綠茶'},
            {'name': '焦糖奶茶', 'milk_type': 'both', 'description': '焦糖風味奶茶'},
            {'name': '紅茶拿鐵', 'milk_type': 'fresh_milk', 'description': '紅茶鮮奶'},
        ]

        success_count = 0

        for shop in shops:
            # 每家店隨機建立 3-5 種飲料
            import random
            drinks_to_create = random.sample(common_drinks, min(5, len(common_drinks)))

            for drink_data in drinks_to_create:
                # 隨機價格
                small_price = random.choice([30, 35, 40, 45])
                medium_price = small_price + 10
                large_price = medium_price + 10

                try:
                    Drink.objects.create(
                        tea_shop=shop,
                        name=drink_data['name'],
                        description=drink_data['description'],
                        milk_type=drink_data['milk_type'],
                        has_small=True,
                        price_small=small_price,
                        has_medium=True,
                        price_medium=medium_price,
                        has_large=True,
                        price_large=large_price,
                    )
                    success_count += 1
                except Exception as e:
                    self.stdout.write(
                        self.style.WARNING(f'跳過重複: {shop.name} - {drink_data["name"]}')
                    )

        self.stdout.write(
            self.style.SUCCESS(f'成功建立 {success_count} 個飲料品項!')
        )
