import csv
from django.core.management.base import BaseCommand
from polls.models import TeaShop


class Command(BaseCommand):
    help = '從 CSV 檔案匯入奶茶店資料'

    def handle(self, *args, **kwargs):
        csv_path = r"C:\Users\love7\OneDrive\桌面\angus'\djagggg\奶茶尋_店家.csv"

        # 清空現有資料（可選）
        TeaShop.objects.all().delete()
        self.stdout.write(self.style.WARNING('已清空現有資料'))

        success_count = 0
        error_count = 0

        with open(csv_path, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)

            for row in reader:
                try:
                    # 處理空值的電話欄位
                    phone = row['phone'].strip() if row['phone'] else None

                    TeaShop.objects.create(
                        place_id=row['place_id'],
                        name=row['name'],
                        address=row['address'],
                        phone=phone,
                        latitude=row['latitude'],
                        longitude=row['longitude'],
                        rating=row['rating'],
                        opening_hours=row['opening_hours'],
                    )
                    success_count += 1
                except Exception as e:
                    error_count += 1
                    self.stdout.write(
                        self.style.ERROR(f'匯入失敗: {row["name"]} - {str(e)}')
                    )

        self.stdout.write(
            self.style.SUCCESS(f'匯入完成! 成功: {success_count}, 失敗: {error_count}')
        )
