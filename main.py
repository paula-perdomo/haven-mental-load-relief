import flet as ft
from app.ui import build_ui
from app.database import init_db

def main(page: ft.Page):
    init_db()
    page.title = "Haven: Mental Load Relief"
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 20
    page.scroll = ft.ScrollMode.ADAPTIVE
    page.vertical_alignment = ft.MainAxisAlignment.START
    
    build_ui(page)

if __name__ == "__main__":
    # For Android packaging with Flet, it runs as a standard Flet app.
    # The `flet build apk` command will package this.
    ft.app(target=main)
