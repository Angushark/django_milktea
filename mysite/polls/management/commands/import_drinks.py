import csv
from decimal import Decimal, InvalidOperation
from django.core.management.base import BaseCommand
from polls.models import TeaShop, Drink


class Command(BaseCommand):
    help = '從 CSV 檔案匯入飲料資料，支援新增與更新'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='匯入前清空所有飲料資料'
        )
        parser.add_argument(
            '--csv-path',
            type=str,
            default=r"C:\Users\love7\OneDrive\桌面\angus'\djagggg\奶茶尋資料.csv",
            help='CSV 檔案路徑'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='模擬執行，不實際寫入資料庫'
        )

    def handle(self, *args, **options):
        csv_path = options['csv_path']
        clear = options['clear']
        dry_run = options['dry_run']

        if dry_run:
            self.stdout.write(self.style.WARNING('--- 乾跑模式：不會實際寫入資料庫 ---'))

        # 清空現有資料（選擇性）
        if clear and not dry_run:
            Drink.objects.all().delete()
            self.stdout.write(self.style.WARNING('已清空現有飲料資料'))

        # 建立店家快取
        self.shop_cache = {shop.name: shop for shop in TeaShop.objects.all()}
        self.stdout.write(f'已載入 {len(self.shop_cache)} 家店家')

        # 統計資訊
        stats = {
            'created': 0,
            'updated': 0,
            'skipped': 0,
            'shop_not_found': [],
            'errors': []
        }

        try:
            with open(csv_path, 'r', encoding='utf-8') as file:
                reader = csv.DictReader(file)

                for row_num, row in enumerate(reader, start=2):
                    try:
                        result = self.process_drink_row(row, dry_run)
                        if result['status'] == 'created':
                            stats['created'] += 1
                        elif result['status'] == 'updated':
                            stats['updated'] += 1
                        elif result['status'] == 'skipped':
                            stats['skipped'] += 1
                        elif result['status'] == 'shop_not_found':
                            stats['shop_not_found'].append(result['detail'])
                    except Exception as e:
                        error_msg = f'第 {row_num} 行: {str(e)}'
                        stats['errors'].append(error_msg)
                        self.stdout.write(self.style.ERROR(f'錯誤 - {error_msg}'))

        except FileNotFoundError:
            self.stdout.write(self.style.ERROR(f'找不到 CSV 檔案: {csv_path}'))
            return
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'讀取 CSV 時發生錯誤: {str(e)}'))
            return

        # 顯示統計報告
        self.stdout.write('\n' + '=' * 50)
        self.stdout.write(self.style.SUCCESS('匯入完成統計:'))
        self.stdout.write(f'  新增: {stats["created"]} 筆')
        self.stdout.write(f'  更新: {stats["updated"]} 筆')
        self.stdout.write(f'  跳過(無變更): {stats["skipped"]} 筆')

        if stats['shop_not_found']:
            self.stdout.write(self.style.WARNING(f'  店家不存在: {len(stats["shop_not_found"])} 筆'))
            for detail in stats['shop_not_found'][:5]:  # 只顯示前 5 筆
                self.stdout.write(f'    - {detail}')
            if len(stats['shop_not_found']) > 5:
                self.stdout.write(f'    ... 還有 {len(stats["shop_not_found"]) - 5} 筆')

        if stats['errors']:
            self.stdout.write(self.style.ERROR(f'  錯誤: {len(stats["errors"])} 筆'))
            for error in stats['errors'][:5]:  # 只顯示前 5 筆
                self.stdout.write(f'    - {error}')
            if len(stats['errors']) > 5:
                self.stdout.write(f'    ... 還有 {len(stats["errors"]) - 5} 筆')

        self.stdout.write('=' * 50)

    def process_drink_row(self, row, dry_run=False):
        """處理單筆飲料資料"""
        # 1. 查詢店家
        shop_name = row['所屬店家'].strip()
        tea_shop = self.shop_cache.get(shop_name)

        if not tea_shop:
            return {
                'status': 'shop_not_found',
                'detail': f'店家不存在: {shop_name}'
            }

        # 2. 解析所有欄位
        drink_data = {
            'name': row['飲料名稱'].strip(),
            'description': row['描述'].strip() if row['描述'].strip() else None,
            'milk_type': self.parse_milk_type(row['奶類']),
            'tea_type': self.parse_tea_type(row['茶類']),
            'topping': self.parse_topping(row['配料']),
            'has_small': self.parse_boolean(row['小杯']),
            'price_small': self.parse_price(row['小杯價格']),
            'has_medium': self.parse_boolean(row['中杯']),
            'price_medium': self.parse_price(row['中杯價格']),
            'has_large': self.parse_boolean(row['大杯']),
            'price_large': self.parse_price(row['大杯價格']),
        }

        # 3. 查詢是否已存在
        try:
            existing_drink = Drink.objects.get(
                tea_shop=tea_shop,
                name=drink_data['name']
            )

            # 4. 檢查是否需要更新
            needs_update = False
            for field, new_value in drink_data.items():
                if field == 'name':  # Skip name (already matched)
                    continue
                old_value = getattr(existing_drink, field)

                # 比較值時處理 Decimal 和 None
                if isinstance(old_value, Decimal) and isinstance(new_value, Decimal):
                    if old_value != new_value:
                        needs_update = True
                        break
                elif old_value != new_value:
                    needs_update = True
                    break

            if needs_update:
                if not dry_run:
                    for field, value in drink_data.items():
                        setattr(existing_drink, field, value)
                    existing_drink.save()
                return {
                    'status': 'updated',
                    'detail': f'{shop_name} - {drink_data["name"]}'
                }
            else:
                return {
                    'status': 'skipped',
                    'detail': f'{shop_name} - {drink_data["name"]}'
                }

        except Drink.DoesNotExist:
            # 5. 建立新飲料
            if not dry_run:
                Drink.objects.create(tea_shop=tea_shop, **drink_data)
            return {
                'status': 'created',
                'detail': f'{shop_name} - {drink_data["name"]}'
            }

    def parse_milk_type(self, value):
        """解析奶類欄位"""
        value = value.strip() if value else ''
        if value == '奶精':
            return 'creamer'
        elif value == '鮮奶':
            return 'fresh_milk'
        return 'none'  # 預設為無奶類

    def parse_boolean(self, value):
        """解析有/無欄位"""
        value = value.strip() if value else ''
        return value == '有'

    def parse_tea_type(self, value):
        """解析茶類欄位"""
        value = value.strip() if value else ''
        mapping = {
            '紅茶': 'black_tea',
            '綠茶': 'green_tea',
            '烏龍茶': 'oolong_tea',
            '青茶': 'blue_tea',
            '抹茶': 'matcha',
        }
        return mapping.get(value, None)

    def parse_topping(self, value):
        """解析配料欄位"""
        value = value.strip() if value else ''
        if value == '有':
            return 'yes'
        elif value == '無':
            return 'no'
        return None

    def parse_price(self, value):
        """解析價格欄位"""
        value = value.strip() if value else ''
        if not value:
            return None
        try:
            return Decimal(value)
        except (InvalidOperation, ValueError):
            return None
