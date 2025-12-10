import csv
import os
import time
import requests
from django.core.management.base import BaseCommand
from django.conf import settings


class Command(BaseCommand):
    help = '根據奶茶尋_店家.csv抓取店家招牌照片'

    def add_arguments(self, parser):
        parser.add_argument(
            '--csv-path',
            type=str,
            default='奶茶尋_店家.csv',
            help='CSV檔案路徑 (預設: 奶茶尋_店家.csv)'
        )
        parser.add_argument(
            '--api-key',
            type=str,
            required=True,
            help='Google Places API Key (必填)'
        )
        parser.add_argument(
            '--delay',
            type=float,
            default=0.5,
            help='每次請求之間的延遲秒數 (預設: 0.5)'
        )
        parser.add_argument(
            '--skip-existing',
            action='store_true',
            help='跳過已存在的圖片'
        )

    def handle(self, *args, **options):
        csv_path = options['csv_path']
        api_key = options['api_key']
        delay = options['delay']
        skip_existing = options['skip_existing']

        # 建立圖片儲存目錄
        # 使用專案根目錄下的 static/shop_images
        base_dir = settings.BASE_DIR.parent  # 從 mysite 往上一層
        images_dir = os.path.join(base_dir, 'mysite', 'static', 'shop_images')

        if not os.path.exists(images_dir):
            os.makedirs(images_dir)
            self.stdout.write(self.style.SUCCESS(f'建立目錄: {images_dir}'))

        # 檢查CSV檔案是否存在
        if not os.path.isabs(csv_path):
            csv_path = os.path.join(base_dir, csv_path)

        if not os.path.exists(csv_path):
            self.stdout.write(self.style.ERROR(f'找不到CSV檔案: {csv_path}'))
            return

        # 統計資訊
        total = 0
        success = 0
        skipped = 0
        failed = 0

        self.stdout.write(self.style.SUCCESS(f'開始處理: {csv_path}'))
        self.stdout.write(self.style.SUCCESS(f'圖片儲存位置: {images_dir}'))
        self.stdout.write('-' * 80)

        with open(csv_path, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)

            for row in reader:
                total += 1
                place_id = row['place_id']
                shop_name = row['name']

                # 檢查檔案是否已存在
                jpg_path = os.path.join(images_dir, f'{place_id}.jpg')
                png_path = os.path.join(images_dir, f'{place_id}.png')

                if skip_existing and (os.path.exists(jpg_path) or os.path.exists(png_path)):
                    self.stdout.write(self.style.WARNING(
                        f'[{total}] 跳過 (已存在): {shop_name} ({place_id})'
                    ))
                    skipped += 1
                    continue

                self.stdout.write(f'[{total}] 處理中: {shop_name} ({place_id})')

                try:
                    # 使用 Google Places API 取得照片
                    photo_reference = self.get_photo_reference(place_id, api_key)

                    if photo_reference:
                        # 下載照片
                        image_data = self.download_photo(photo_reference, api_key)

                        if image_data:
                            # 儲存為 JPG
                            with open(jpg_path, 'wb') as img_file:
                                img_file.write(image_data)

                            self.stdout.write(self.style.SUCCESS(
                                f'    ✓ 成功下載: {place_id}.jpg'
                            ))
                            success += 1
                        else:
                            self.stdout.write(self.style.ERROR(
                                f'    ✗ 下載失敗: 無法取得圖片資料'
                            ))
                            failed += 1
                    else:
                        self.stdout.write(self.style.ERROR(
                            f'    ✗ 失敗: 找不到照片參考'
                        ))
                        failed += 1

                except Exception as e:
                    self.stdout.write(self.style.ERROR(
                        f'    ✗ 錯誤: {str(e)}'
                    ))
                    failed += 1

                # 延遲以避免超過API請求限制
                time.sleep(delay)

        # 顯示統計資訊
        self.stdout.write('-' * 80)
        self.stdout.write(self.style.SUCCESS('處理完成！'))
        self.stdout.write(f'總計: {total}')
        self.stdout.write(self.style.SUCCESS(f'成功: {success}'))
        if skipped > 0:
            self.stdout.write(self.style.WARNING(f'跳過: {skipped}'))
        if failed > 0:
            self.stdout.write(self.style.ERROR(f'失敗: {failed}'))

    def get_photo_reference(self, place_id, api_key):
        """
        使用 Place ID 取得照片參考
        """
        url = 'https://maps.googleapis.com/maps/api/place/details/json'
        params = {
            'place_id': place_id,
            'fields': 'photos',
            'key': api_key
        }

        response = requests.get(url, params=params)
        data = response.json()

        if data.get('status') == 'OK':
            result = data.get('result', {})
            photos = result.get('photos', [])

            if photos:
                # 取得第一張照片的 photo_reference
                return photos[0].get('photo_reference')

        return None

    def download_photo(self, photo_reference, api_key, max_width=800):
        """
        使用 photo_reference 下載照片
        """
        url = 'https://maps.googleapis.com/maps/api/place/photo'
        params = {
            'photo_reference': photo_reference,
            'maxwidth': max_width,
            'key': api_key
        }

        response = requests.get(url, params=params)

        if response.status_code == 200:
            return response.content

        return None
