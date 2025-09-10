"""
画像ファイル変換モジュール
要件定義書 F-102, F-103 画像ファイルのPDF変換実装
"""

from pathlib import Path
from typing import List, Tuple
import math

try:
    from PIL import Image, ImageDraw, ImageFont
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import A4, letter
    from reportlab.lib.utils import ImageReader
except ImportError as e:
    print(f"画像変換ライブラリ未インストール: {e}")

from ..utils.logger import logger
from ..config import SUPPORTED_IMAGE_EXTENSIONS


class ImageConverter:
    """画像ファイルからPDF変換を行うクラス"""
    
    def __init__(self):
        self.supported_formats = SUPPORTED_IMAGE_EXTENSIONS
        logger.info("画像コンバーター初期化完了")
    
    def convert_to_pdf(self, input_path: str, output_path: str) -> bool:
        """
        画像ファイルのPDF変換
        
        Args:
            input_path: 入力画像ファイルパス
            output_path: 出力PDFパス
            
        Returns:
            bool: 変換成功時True
        """
        try:
            file_ext = Path(input_path).suffix.lower()
            
            if file_ext not in self.supported_formats:
                logger.error(f"未対応の画像形式: {file_ext}")
                return False
            
            # 画像をPDFに変換
            if self._convert_single_image(input_path, output_path):
                logger.info(f"画像変換完了: {Path(input_path).name}")
                return True
            else:
                return False
        
        except Exception as e:
            logger.error(f"画像変換エラー: {input_path} - {str(e)}", exc_info=True)
            return False
    
    def convert_multiple_images_to_pdf(self, image_paths: List[str], output_path: str) -> bool:
        """
        複数画像を1つのPDFに変換
        
        Args:
            image_paths: 画像ファイルパスのリスト
            output_path: 出力PDFパス
            
        Returns:
            bool: 変換成功時True
        """
        try:
            c = canvas.Canvas(output_path, pagesize=A4)
            page_width, page_height = A4
            
            for i, image_path in enumerate(image_paths):
                if i > 0:  # 2ページ目以降は改ページ
                    c.showPage()
                
                # 画像をページに配置
                if not self._add_image_to_canvas(c, image_path, page_width, page_height):
                    logger.warning(f"画像追加失敗: {image_path}")
                    continue
            
            c.save()
            logger.info(f"複数画像変換完了: {len(image_paths)}枚 -> {Path(output_path).name}")
            return True
        
        except Exception as e:
            logger.error(f"複数画像変換エラー: {str(e)}", exc_info=True)
            return False
    
    def _convert_single_image(self, input_path: str, output_path: str) -> bool:
        """単一画像のPDF変換"""
        try:
            # PILで画像を開く
            with Image.open(input_path) as img:
                # RGBAをRGBに変換（PDF対応）
                if img.mode in ('RGBA', 'LA', 'P'):
                    background = Image.new('RGB', img.size, (255, 255, 255))
                    if img.mode == 'P':
                        img = img.convert('RGBA')
                    background.paste(img, mask=img.split()[-1] if len(img.split()) == 4 else None)
                    img = background
                elif img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # PDF作成
                c = canvas.Canvas(output_path, pagesize=A4)
                page_width, page_height = A4
                
                return self._add_image_to_canvas_with_pil(c, img, page_width, page_height, input_path)
        
        except Exception as e:
            logger.error(f"単一画像変換エラー: {input_path} - {str(e)}")
            return False
    
    def _add_image_to_canvas(self, canvas_obj: canvas.Canvas, image_path: str, 
                           page_width: float, page_height: float) -> bool:
        """画像をキャンバスに追加（ファイルパス版）"""
        try:
            img_reader = ImageReader(image_path)
            img_width, img_height = img_reader.getSize()
            
            # 画像サイズを計算してページに収める
            scale_x = (page_width - 40) / img_width  # マージン20px
            scale_y = (page_height - 40) / img_height
            scale = min(scale_x, scale_y, 1.0)  # 縮小のみ
            
            new_width = img_width * scale
            new_height = img_height * scale
            
            # 中央配置
            x = (page_width - new_width) / 2
            y = (page_height - new_height) / 2
            
            canvas_obj.drawImage(img_reader, x, y, width=new_width, height=new_height)
            canvas_obj.save()
            
            return True
        
        except Exception as e:
            logger.error(f"画像追加エラー: {image_path} - {str(e)}")
            return False
    
    def _add_image_to_canvas_with_pil(self, canvas_obj: canvas.Canvas, pil_image: Image.Image,
                                    page_width: float, page_height: float, source_path: str) -> bool:
        """画像をキャンバスに追加（PIL Image版）"""
        try:
            img_width, img_height = pil_image.size
            
            # 画像サイズを計算してページに収める
            margin = 40
            scale_x = (page_width - margin) / img_width
            scale_y = (page_height - margin) / img_height
            scale = min(scale_x, scale_y, 1.0)  # 縮小のみ
            
            new_width = img_width * scale
            new_height = img_height * scale
            
            # 中央配置
            x = (page_width - new_width) / 2
            y = (page_height - new_height) / 2
            
            # PIL ImageをImageReaderに変換
            img_reader = ImageReader(pil_image)
            canvas_obj.drawImage(img_reader, x, y, width=new_width, height=new_height)
            
            # ファイル情報をフッターに追加
            canvas_obj.setFont("Helvetica", 8)
            canvas_obj.drawString(20, 20, f"Source: {Path(source_path).name}")
            
            canvas_obj.save()
            return True
        
        except Exception as e:
            logger.error(f"PIL画像追加エラー: {source_path} - {str(e)}")
            return False
    
    def get_image_info(self, image_path: str) -> dict:
        """画像情報の取得"""
        try:
            with Image.open(image_path) as img:
                return {
                    'format': img.format,
                    'mode': img.mode,
                    'size': img.size,
                    'width': img.width,
                    'height': img.height
                }
        except Exception as e:
            logger.error(f"画像情報取得エラー: {image_path} - {str(e)}")
            return {}
    
    def is_supported_format(self, file_path: str) -> bool:
        """対応形式チェック"""
        file_ext = Path(file_path).suffix.lower()
        return file_ext in self.supported_formats