import flet as ft
import requests
import sqlite3
from datetime import datetime

# APIエンドポイントの定義
AREA_URL = "http://www.jma.go.jp/bosai/common/const/area.json"
WEATHER_URL = "https://www.jma.go.jp/bosai/forecast/data/forecast/{area_code}.json"

# データベース設定
DB_PATH = 'weather_forecast.db'

def init_database():
    """データベースの初期化と必要なテーブルの作成"""
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    
    # 天気予報データを保存するテーブル
    cur.execute('''
    CREATE TABLE IF NOT EXISTS weather_forecasts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        region_name TEXT,
        date TEXT,
        weather TEXT,
        max_temp TEXT,
        min_temp TEXT,
        weather_code TEXT,
        fetched_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    con.commit()
    con.close()

def fetch_area_list():
    try:
        response = requests.get(AREA_URL)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"地域リストの取得に失敗: {e}")
        return None

def fetch_weather(area_code):
    try:
        response = requests.get(WEATHER_URL.format(area_code=area_code))
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"天気情報の取得に失敗 (地域コード: {area_code}): {e}")
        return None

def find_matching_area(area_data, weather_data, target_name):
    if area_data is None or weather_data is None:
        return None, None
    
    for series in weather_data[0]["timeSeries"]:
        matching_areas = [
            area for area in series["areas"] 
            if any(target_name in subname for subname in [area["area"]["name"], target_name])
        ]
        
        if matching_areas:
            return matching_areas[0], series["timeDefines"]
    
    return None, None

def save_weather_data(region_name, weather_data):
    """天気データをデータベースに保存"""
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    
    # 既存のデータを削除（同じ地域の古いデータを上書き）
    cur.execute("DELETE FROM weather_forecasts WHERE region_name = ?", (region_name,))
    
    # 天気コードとアイコンの対応表
    weather_code_map = {
        "晴れ": "100", "晴時々曇": "101", "晴一時曇": "102",
        "晴時々雨": "103", "晴一時雨": "104", "晴時々雪": "105",
        "晴一時雪": "106", "曇り": "200", "曇時々晴": "201",
        "曇一時晴": "202", "曇時々雨": "203", "曇一時雨": "204",
        "曇時々雪": "205", "曇一時雪": "206", "雨": "300", "雪": "400"
    }
    
    # マッチングエリアと時間情報の取得
    matching_area, time_defines = find_matching_area(fetch_area_list(), weather_data, region_name)
    
    if matching_area and time_defines:
        # データベースに保存するデータを準備
        forecast_data = []
        for time_idx, time in enumerate(time_defines):
            if "weathers" in matching_area:
                weather = matching_area["weathers"][time_idx] if time_idx < len(matching_area["weathers"]) else "情報なし"
                
                # 気温情報の取得
                max_temp = matching_area["tempsMax"][time_idx] if "tempsMax" in matching_area and time_idx < len(matching_area["tempsMax"]) else ""
                min_temp = matching_area["tempsMin"][time_idx] if "tempsMin" in matching_area and time_idx < len(matching_area["tempsMin"]) else ""
                
                # 天気コードの取得
                weather_code = "100"  # デフォルト
                for key, code in weather_code_map.items():
                    if key in weather:
                        weather_code = code
                        break
                
                # 日付のフォーマット
                date = time.split("T")[0]
                
                forecast_data.append((
                    region_name, date, weather, max_temp, min_temp, weather_code
                ))
        
        # データベースに一括挿入
        cur.executemany('''
            INSERT INTO weather_forecasts 
            (region_name, date, weather, max_temp, min_temp, weather_code) 
            VALUES (?, ?, ?, ?, ?, ?)
        ''', forecast_data)
        
        con.commit()
        con.close()
        return True
    
    con.close()
    return False

def fetch_weather_from_database(region_name):
    """データベースから特定の地域の天気データを取得"""
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    
    cur.execute('''
        SELECT date, weather, max_temp, min_temp, weather_code 
        FROM weather_forecasts 
        WHERE region_name = ? 
        ORDER BY date
    ''', (region_name,))
    
    results = cur.fetchall()
    con.close()
    
    return results

def print_database_contents(region_name=None):
    """データベースの内容を表示"""
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    
    if region_name:
        cur.execute('''
            SELECT * FROM weather_forecasts 
            WHERE region_name = ?
            ORDER BY date
        ''', (region_name,))
    else:
        cur.execute('SELECT * FROM weather_forecasts ORDER BY fetched_at DESC')
    
    print("\n--- データベース内容 ---")
    for row in cur.fetchall():
        print(f"ID: {row[0]}, 地域: {row[1]}, 日付: {row[2]}, "
              f"天気: {row[3]}, 最高気温: {row[4]}, 最低気温: {row[5]}, "
              f"天気コード: {row[6]}, 取得日時: {row[7]}")
    
    # 基本統計情報
    cur.execute('SELECT COUNT(*) FROM weather_forecasts')
    total_records = cur.fetchone()[0]
    print(f"\n総レコード数: {total_records}")
    
    con.close()

def main(page: ft.Page):
    # データベースの初期化
    init_database()
    
    page.title = "気象庁天気予報アプリ"
    page.vertical_alignment = ft.MainAxisAlignment.CENTER

    def show_weather(e, region_code, region_name):
        weather_data = fetch_weather(region_code)
        
        if not weather_data:
            page.add(ft.Text("天気情報を取得できません", color="red"))
            return

        # データベースに保存
        if save_weather_data(region_name, weather_data):
            # データベース内容の確認（開発時のデバッグ用）
            print_database_contents(region_name)
        
        # 天気データの表示
        weather_info = fetch_weather_from_database(region_name)
        
        weather_cards = []
        for date, weather, max_temp, min_temp, weather_code in weather_info:
            card = ft.Card(
                content=ft.Container(
                    content=ft.Column(
                        [
                            ft.Text(date, size=16, weight=ft.FontWeight.BOLD),
                            ft.Image(
                                src=f"https://www.jma.go.jp/bosai/forecast/img/{weather_code}.svg",
                                width=50,
                                height=50,
                            ),
                            ft.Text(weather),
                            ft.Text(
                                f"{min_temp}°C / {max_temp}°C" if min_temp and max_temp else "",
                                color=ft.colors.BLUE if min_temp else None
                            ),
                        ],
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=10,
                    ),
                    padding=10,
                ),
                width=200,
            )
            weather_cards.append(card)

        page.controls.clear()
        page.add(
            ft.Column(
                [
                    ft.Text(f"{region_name}の天気予報", size=24, weight=ft.FontWeight.BOLD),
                    ft.Row(
                        weather_cards,
                        scroll=ft.ScrollMode.AUTO,
                        spacing=10,
                    ),
                    ft.ElevatedButton("戻る", on_click=show_main_menu, width=300)
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=20
            )
        )
        page.update()

    def show_regions(region_code):
        area_data = fetch_area_list()
        if not area_data:
            page.add(ft.Text("地域情報の取得に失敗しました", color="red"))
            return

        children = area_data["centers"][region_code]["children"]

        region_buttons = []
        for code in children:
            region_info = area_data["offices"][code]
            region_name = region_info["name"]
            button = ft.OutlinedButton(
                text=region_name, 
                on_click=lambda e, rc=code, rn=region_name: show_weather(e, rc, rn),
                width=300
            )
            region_buttons.append(button)

        page.controls.clear()
        page.add(
            ft.Column(
                [
                    ft.Text("地域を選択してください", size=20, weight=ft.FontWeight.BOLD),
                    ft.Column(region_buttons, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                    ft.ElevatedButton("戻る", on_click=show_main_menu, width=300)
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=10
            )
        )
        page.update()

    def show_main_menu(e=None):
        page.controls.clear()
        page.scroll = "auto"  # スクロール可能にする
        page.add(
            ft.Column(
                [
                    ft.Text("気象庁天気予報アプリ", size=24, weight=ft.FontWeight.BOLD),
                    ft.ElevatedButton("北海道地方", on_click=lambda e: show_regions("010100"), width=300),
                    ft.ElevatedButton("東北地方", on_click=lambda e: show_regions("010200"), width=300),
                    ft.ElevatedButton("関東甲信地方", on_click=lambda e: show_regions("010300"), width=300),
                    ft.ElevatedButton("東海地方", on_click=lambda e: show_regions("010400"), width=300),
                    ft.ElevatedButton("北陸地方", on_click=lambda e: show_regions("010500"), width=300),
                    ft.ElevatedButton("近畿地方", on_click=lambda e: show_regions("010600"), width=300),
                    ft.ElevatedButton("中国地方", on_click=lambda e: show_regions("010700"), width=300),
                    ft.ElevatedButton("四国地方", on_click=lambda e: show_regions("010800"), width=300),
                    ft.ElevatedButton("九州北部地方", on_click=lambda e: show_regions("010900"), width=300),
                    ft.ElevatedButton("九州南部・奄美地方", on_click=lambda e: show_regions("011000"), width=300),
                    ft.ElevatedButton("沖縄地方", on_click=lambda e: show_regions("011100"), width=300),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                alignment=ft.MainAxisAlignment.CENTER,
                spacing=20
            )
        )
        page.update()

    show_main_menu()

if __name__ == "__main__":
    ft.app(target=main)