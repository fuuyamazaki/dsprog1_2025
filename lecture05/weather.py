import flet as ft
import requests

# APIエンドポイントの定義
AREA_URL = "http://www.jma.go.jp/bosai/common/const/area.json"
WEATHER_URL = "https://www.jma.go.jp/bosai/forecast/data/forecast/{area_code}.json"

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
    for series in weather_data[0]["timeSeries"]:
        matching_areas = [
            area for area in series["areas"] 
            if any(target_name in subname for subname in [area["area"]["name"], target_name])
        ]
        
        if matching_areas:
            return matching_areas[0], series["timeDefines"]
    
    return None, None

def main(page: ft.Page):
    page.title = "気象庁天気予報アプリ"
    page.vertical_alignment = ft.MainAxisAlignment.CENTER

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

    def show_weather(e, region_code, region_name):
        weather_data = fetch_weather(region_code)
        area_data = fetch_area_list()

        if not weather_data:
            page.add(ft.Text("天気情報を取得できません", color="red"))
            return

        # 天気コードとアイコンの対応表
        weather_code_map = {
            "晴れ": "100",
            "晴時々曇": "101",
            "晴一時曇": "102",
            "晴時々雨": "103",
            "晴一時雨": "104",
            "晴時々雪": "105",
            "晴一時雪": "106",
            "曇り": "200",
            "曇時々晴": "201",
            "曇一時晴": "202",
            "曇時々雨": "203",
            "曇一時雨": "204",
            "曇時々雪": "205",
            "曇一時雪": "206",
            "雨": "300",
            "雪": "400",
            # 必要に応じて他の天気コードも追加
        }

        weather_info = [ft.Text(f"{region_name}の天気予報", size=20, weight=ft.FontWeight.BOLD)]

        matching_area, time_defines = find_matching_area(area_data, weather_data, region_name)

        if matching_area and time_defines:
            # 日付ごとの天気情報をカードで表示
            weather_cards = []
            
            if "weathers" in matching_area:
                for time, weather in zip(time_defines, matching_area.get("weathers", [])):
                    # 最高気温と最低気温を取得
                    max_temp = ""
                    min_temp = ""
                    if "tempsMax" in matching_area:
                        max_temp = matching_area["tempsMax"][time_defines.index(time)]
                    if "tempsMin" in matching_area:
                        min_temp = matching_area["tempsMin"][time_defines.index(time)]

                    # 天気コードを取得
                    weather_code = "100"  # デフォルト
                    for key, code in weather_code_map.items():
                        if key in weather:
                            weather_code = code
                            break

                    # 日付のフォーマット
                    date = time.split("T")[0]

                    # カードの作成
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

            # カードを横に並べて表示
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

    def show_hokkaido_regions(e):
        show_regions("010100")

    def show_tohoku_regions(e):
        show_regions("010200")

    def show_kanto_koshin_regions(e):
        show_regions("010300")

    def show_tokai_regions(e):
        show_regions("010400")

    def show_hokuriku_regions(e):
        show_regions("010500")

    def show_kinki_regions(e):
        show_regions("010600")

    def show_chugoku_regions(e):
        show_regions("010700")

    def show_shikoku_regions(e):
        show_regions("010800")

    def show_kyushu_north_regions(e):
        show_regions("010900")

    def show_kyushu_south_regions(e):
        show_regions("011000")

    def show_okinawa_regions(e):
        show_regions("011100")

    def show_main_menu(e=None):
        page.controls.clear()
        page.scroll = "auto"  # スクロール可能にする
        page.add(
            ft.Column(
                [
                    ft.Text("気象庁天気予報アプリ", size=24, weight=ft.FontWeight.BOLD),
                    ft.ElevatedButton("北海道地方", on_click=show_hokkaido_regions, width=300),
                    ft.ElevatedButton("東北地方", on_click=show_tohoku_regions, width=300),
                    ft.ElevatedButton("関東甲信地方", on_click=show_kanto_koshin_regions, width=300),
                    ft.ElevatedButton("東海地方", on_click=show_tokai_regions, width=300),
                    ft.ElevatedButton("北陸地方", on_click=show_hokuriku_regions, width=300),
                    ft.ElevatedButton("近畿地方", on_click=show_kinki_regions, width=300),
                    ft.ElevatedButton("中国地方", on_click=show_chugoku_regions, width=300),
                    ft.ElevatedButton("四国地方", on_click=show_shikoku_regions, width=300),
                    ft.ElevatedButton("九州北部地方", on_click=show_kyushu_north_regions, width=300),
                    ft.ElevatedButton("九州南部・奄美地方", on_click=show_kyushu_south_regions, width=300),
                    ft.ElevatedButton("沖縄地方", on_click=show_okinawa_regions, width=300),
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