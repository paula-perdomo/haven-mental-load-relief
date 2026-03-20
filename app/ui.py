import flet as ft
from app.agent import process_user_input

def build_ui(page: ft.Page):
    selected_file_path = [None]

    async def pick_file(e):
        files = await ft.FilePicker().pick_files(
            allow_multiple=False,
            with_data=True,
            file_type=ft.FilePickerFileType.CUSTOM,
            allowed_extensions=["pdf", "png", "jpg", "jpeg"],
        )
        if files:
            selected_file_path[0] = files[0].path
            attach_button.icon_color = ft.Colors.GREEN_400
            page.update()

    # ---- CHAT TAB ----
    chat_view = ft.ListView(
        expand=True,
        spacing=10,
        auto_scroll=True,
    )

    def send_message(e):
        user_text = message_input.value
        path = selected_file_path[0]
        
        if not user_text and not path:
            return
        
        if path:
            chat_view.controls.append(ft.Text(f"You attached: {path}", color=ft.Colors.PURPLE_200))
        if user_text:
            chat_view.controls.append(ft.Text(f"You: {user_text}", color=ft.Colors.BLUE_200))

        message_input.value = ""
        attach_button.icon_color = ft.Colors.GREY_400
        page.update()
        
        loading = ft.ProgressRing(width=16, height=16, stroke_width=2)
        loading_row = ft.Row([ft.Text("Haven Copilot reading... "), loading])
        chat_view.controls.append(loading_row)
        page.update()
        
        try:
            response = process_user_input(user_text, path if path else None)
        except Exception as ex:
            response = str(ex)
        
        selected_file_path[0] = None
        
        chat_view.controls.remove(loading_row)
        chat_view.controls.append(ft.Text(f"Haven AI:\n{response}", color=ft.Colors.LIGHT_GREEN_200))
        page.update()

    message_input = ft.TextField(
        hint_text="Ask about the schedule or attach a calendar image...",
        expand=True,
        on_submit=send_message,
        multiline=True,
        min_lines=1,
        max_lines=3
    )

    attach_button = ft.IconButton(
        icon=ft.Icons.ATTACH_FILE,
        on_click=pick_file,
        icon_color=ft.Colors.GREY_400
    )
    
    send_button = ft.IconButton(
        icon=ft.Icons.SEND_ROUNDED,
        on_click=send_message,
        icon_color=ft.Colors.BLUE_400
    )

    chat_tab_content = ft.Column([
        chat_view,
        ft.Row([attach_button, message_input, send_button], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
    ], expand=True)

    # ---- SCHEDULE TAB ----
    schedule_view = ft.Column([
        ft.Text("This week's activities will appear here.", color=ft.Colors.GREY_400)
    ], expand=True)

    # ---- MAIN LAYOUT ----
    main_container = ft.Container(content=chat_tab_content, expand=True)

    def switch_tab(e):
        idx = e.control.selected_index
        if idx == 0:
            main_container.content = chat_tab_content
        elif idx == 1:
            main_container.content = schedule_view
        page.update()

    page.navigation_bar = ft.NavigationBar(
        destinations=[
            ft.NavigationBarDestination(icon=ft.Icons.CHAT, label="Chat"),
            ft.NavigationBarDestination(icon=ft.Icons.CALENDAR_MONTH, label="Schedule"),
        ],
        on_change=switch_tab
    )

    page.add(
        ft.Text("Haven", size=24, weight=ft.FontWeight.BOLD),
        main_container
    )
