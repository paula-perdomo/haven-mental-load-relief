import flet as ft
import httpx
from app.agent import process_user_input
import app.database as db

def build_ui(page: ft.Page):
    selected_file_path = [None]

    async def pick_file(e):
        files = await ft.FilePicker().pick_files(
            allow_multiple=False,
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
        controls=[
            ft.Text(
                "Haven AI:\nHi, I'm Haven, your Family Logistics Copilot! I can help you reduce your mental load by automatically parsing complex schedules, managing shared lists, and preparing packing routines. Need help? Just type your thoughts or upload a picture of a school calendar, and I'll organize it for you!", 
                color=ft.Colors.LIGHT_GREEN_200
            )
        ]
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
        loading_row = ft.Row([ft.Text("Haven Copilot thinking... "), loading])
        chat_view.controls.append(loading_row)
        page.update()
        
        response = process_user_input(user_text, path if path else None)
        
        selected_file_path[0] = None
        
        chat_view.controls.remove(loading_row)
        chat_view.controls.append(ft.Text(f"Haven AI:\n{response}", color=ft.Colors.LIGHT_GREEN_200))
        page.update()
        
        # Refresh schedule behind the scenes
        load_schedule()

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
    schedule_list = ft.ListView(expand=True, spacing=10)
    schedule_tab_content = ft.Column([
        ft.Text("Upcoming Activities", size=20, weight=ft.FontWeight.BOLD),
        schedule_list
    ], expand=True)

    def load_schedule():
        schedule_list.controls.clear()
        activities = db.get_activities()
        if not activities:
            schedule_list.controls.append(ft.Text("No activities scheduled yet.", color=ft.Colors.GREY_400))
        else:
            for act in activities:
                items = db.get_prep_items(act["id"])
                items_str = ", ".join([i["item_name"] for i in items]) if items else "Nothing"
                
                card = ft.Card(
                    content=ft.Container(
                        padding=10,
                        content=ft.Column([
                            ft.Text(act["title"], weight=ft.FontWeight.BOLD, size=16),
                            ft.Text(f"{act['day_of_week']} at {act['time_str']}", color=ft.Colors.BLUE_200),
                            ft.Text(f"Pack: {items_str}", color=ft.Colors.GREY_300, italic=True)
                        ])
                    )
                )
                schedule_list.controls.append(card)
        if page.navigation_bar and page.navigation_bar.selected_index == 1:
            page.update()

    # ---- LISTS TAB ----
    lists_main_container = ft.Container(expand=True)
    current_list_id = [None]
    current_list_title = [None]
    
    lists_overview_col = ft.Column(expand=True)
    list_details_col = ft.Column(expand=True)
    
    new_list_input = ft.TextField(label="New List Name", expand=True)
    
    def create_list(e):
        if new_list_input.value:
            db.add_list(new_list_input.value.strip())
            new_list_input.value = ""
            render_lists_overview()
            
    create_list_btn = ft.ElevatedButton("Create List", on_click=create_list)
    
    def open_list_details(e, list_id, title):
        current_list_id[0] = list_id
        current_list_title[0] = title
        render_list_details()
        
    def render_lists_overview():
        lists_overview_col.controls.clear()
        lists_overview_col.controls.append(ft.Text("Shared Lists", size=20, weight=ft.FontWeight.BOLD))
        lists_overview_col.controls.append(ft.Row([new_list_input, create_list_btn]))
        
        lists = db.get_lists()
        if not lists:
            lists_overview_col.controls.append(ft.Text("No lists created yet.", color=ft.Colors.GREY_400))
        else:
            for l in lists:
                card = ft.Card(
                    content=ft.Container(
                        padding=15,
                        ink=True,
                        on_click=lambda e, lid=l["id"], t=l["title"]: open_list_details(e, lid, t),
                        content=ft.Row([
                            ft.Icon(ft.Icons.LIST),
                            ft.Text(l["title"], size=16, weight=ft.FontWeight.W_500)
                        ])
                    )
                )
                lists_overview_col.controls.append(card)
        
        lists_main_container.content = lists_overview_col
        if page.navigation_bar and page.navigation_bar.selected_index == 2:
            page.update()

    # List Details sub-view
    new_item_input = ft.TextField(label="Add Item", expand=True)
    search_item_input = ft.TextField(label="Filter items...", icon=ft.Icons.SEARCH, expand=True)
    items_list_view = ft.ListView(expand=True, spacing=5)
    
    def render_list_details():
        list_details_col.controls.clear()
        
        def back_to_overview(e):
            current_list_id[0] = None
            render_lists_overview()
            
        header = ft.Row([
            ft.IconButton(ft.Icons.ARROW_BACK, on_click=back_to_overview),
            ft.Text(f"List: {current_list_title[0]}", size=20, weight=ft.FontWeight.BOLD)
        ])
        
        def add_item(e):
            val = new_item_input.value.strip()
            if val and current_list_id[0]:
                db.add_list_item(current_list_id[0], val)
                new_item_input.value = ""
                refresh_items_list()
                
        add_item_btn = ft.ElevatedButton("Add", on_click=add_item)
        
        def on_search_change(e):
            refresh_items_list()
            
        search_item_input.on_change = on_search_change
        
        def refresh_items_list():
            items_list_view.controls.clear()
            if not current_list_id[0]: return
            
            # get_list_items already sorts alphabetically by item_name ASC in SQLite
            items = db.get_list_items(current_list_id[0])
            search_query = search_item_input.value.lower() if search_item_input.value else ""
            
            active_items = []
            done_items = []
            for item in items:
                if search_query and search_query not in item["item_name"].lower():
                    continue
                
                def toggle(e, iid=item["id"]):
                    db.toggle_item_status(iid, e.control.value)
                    refresh_items_list()
                    
                cb = ft.Checkbox(label=item["item_name"], value=item["is_done"], on_change=toggle)
                if item["is_done"]:
                    cb.label_style = ft.TextStyle(decoration=ft.TextDecoration.LINE_THROUGH, color=ft.Colors.GREY_500)
                    done_items.append(cb)
                else:
                    active_items.append(cb)
            
            items_list_view.controls.extend(active_items)
            if done_items:
                if active_items:
                    items_list_view.controls.append(ft.Divider())
                items_list_view.controls.extend(done_items)
            page.update()
            
        list_details_col.controls.extend([
            header,
            ft.Row([new_item_input, add_item_btn]),
            search_item_input,
            items_list_view
        ])
        
        refresh_items_list()
        lists_main_container.content = list_details_col
        page.update()


    # ---- HOUSEHOLD TAB ----
    household_col = ft.Column(expand=True)
    new_member_name = ft.TextField(label="Member Name (e.g., Mom)", expand=1)
    new_member_role = ft.TextField(label="Role (e.g., Parent)", expand=1)
    members_list_view = ft.ListView(expand=True, spacing=5)

    def load_members():
        members_list_view.controls.clear()
        mems = db.get_members()
        if not mems:
            members_list_view.controls.append(ft.Text("No household members yet.", color=ft.Colors.GREY_400))
        for m in mems:
            def make_delete_click(mid):
                def on_click(e):
                    db.delete_member(mid)
                    load_members()
                return on_click
                
            def make_edit_click(m_data):
                def on_click(e):
                    edit_name = ft.TextField(label="Name", value=m_data['name'])
                    edit_role = ft.TextField(label="Role", value=m_data['role'])
                    
                    def save_edit(e2):
                        db.update_member(m_data['id'], edit_name.value.strip(), edit_role.value.strip())
                        page.dialog.open = False
                        page.update()
                        load_members()
                        
                    def close_dlg(e2):
                        page.dialog.open = False
                        page.update()
                        
                    dlg = ft.AlertDialog(
                        title=ft.Text("Edit Member"),
                        content=ft.Column([edit_name, edit_role], tight=True),
                        actions=[
                            ft.TextButton("Cancel", on_click=close_dlg),
                            ft.TextButton("Save", on_click=save_edit)
                        ],
                        actions_alignment=ft.MainAxisAlignment.END
                    )
                    page.dialog = dlg
                    dlg.open = True
                    page.update()
                return on_click

            card = ft.Card(
                content=ft.Container(
                    padding=10,
                    content=ft.Row([
                        ft.Row([
                            ft.Icon(ft.Icons.PERSON),
                            ft.Text(f"{m['name']} ({m['role']})", size=16, weight=ft.FontWeight.W_500)
                        ]),
                        ft.Row([
                            ft.IconButton(icon=ft.Icons.EDIT, icon_color=ft.Colors.BLUE, tooltip="Edit", on_click=make_edit_click(m)),
                            ft.IconButton(icon=ft.Icons.DELETE, icon_color=ft.Colors.RED, tooltip="Delete", on_click=make_delete_click(m['id']))
                        ])
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
                )
            )
            members_list_view.controls.append(card)
        if page.navigation_bar and page.navigation_bar.selected_index == 3:
            page.update()

    def add_member_click(e):
        name = new_member_name.value.strip()
        role = new_member_role.value.strip()
        if name and role:
            db.add_member(name, role)
            new_member_name.value = ""
            new_member_role.value = ""
            load_members()

    add_member_btn = ft.ElevatedButton("Add Member", on_click=add_member_click)
    
    household_tab_content = ft.Column([
        ft.Text("Household Database", size=20, weight=ft.FontWeight.BOLD),
        ft.Row([new_member_name, new_member_role]),
        add_member_btn,
        ft.Divider(),
        members_list_view
    ], expand=True)

    # ---- SETTINGS TAB ----
    import os
    server_url_input = ft.TextField(label="Server URL", value=db.get_config("SERVER_URL") or "http://127.0.0.1:8000")
    username_input = ft.TextField(label="Username", value=db.get_config("USERNAME") or "")
    password_input = ft.TextField(label="Password", password=True, can_reveal_password=True)
    settings_status = ft.Text("")
    
    # Google OAuth Infrastructure
    GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "")
    if GOOGLE_CLIENT_ID:
        google_provider = ft.OAuthProvider(
            client_id=GOOGLE_CLIENT_ID,
            client_secret=os.environ.get("GOOGLE_CLIENT_SECRET", ""),
            authorization_endpoint="https://accounts.google.com/o/oauth2/v2/auth",
            token_endpoint="https://oauth2.googleapis.com/token",
            redirect_url="http://localhost:8550/oauth_callback", 
            user_scopes=["email", "profile"]
        )
        def on_google_login(e):
            if e.error:
                settings_status.value = f"Google Login Error: {e.error}"
                settings_status.color = ft.Colors.RED
            else:
                db.set_config("JWT_TOKEN", page.auth.token.access_token)
                settings_status.value = "Google Account Linked!"
                settings_status.color = ft.Colors.GREEN
            page.update()
        page.on_login = on_google_login
        google_login_btn = ft.ElevatedButton("Sign in with Google", on_click=lambda e: page.login(google_provider), icon=ft.Icons.CLOUD_DONE)
    else:
        google_login_btn = ft.ElevatedButton("Sign in with Google (Missing Config)", disabled=True)

    def save_settings(e):
        settings_status.value = "Authenticating..."
        settings_status.color = ft.Colors.AMBER
        page.update()
        
        try:
            url = server_url_input.value.strip()
            # Request JWT
            resp = httpx.post(f"{url}/api/login", data={"username": username_input.value, "password": password_input.value})
            if resp.status_code == 200:
                token = resp.json().get("access_token")
                db.set_config("JWT_TOKEN", token)
                db.set_config("SERVER_URL", url)
                db.set_config("USERNAME", username_input.value)
                settings_status.value = "Connected and saved secure token!"
                settings_status.color = ft.Colors.GREEN
            else:
                settings_status.value = f"Login failed: HTTP {resp.status_code}"
                settings_status.color = ft.Colors.RED
        except Exception as ex:
            settings_status.value = f"Error connecting to server: {ex}"
            settings_status.color = ft.Colors.RED
        
        page.update()

    save_btn = ft.ElevatedButton("Connect & Save", on_click=save_settings)
    
    settings_tab_content = ft.Column([
        ft.Text("Backend Connection", size=20, weight=ft.FontWeight.BOLD),
        server_url_input,
        username_input,
        password_input,
        save_btn,
        ft.Divider(),
        ft.Text("Cloud Sync", size=20, weight=ft.FontWeight.BOLD),
        ft.Text("Config GOOGLE_CLIENT_ID in your env to enable OAuth token exchange.", color=ft.Colors.GREY_500),
        google_login_btn,
        settings_status
    ], expand=True)

    # ---- MAIN LAYOUT ----
    main_container = ft.Container(content=chat_tab_content, expand=True)

    def switch_tab(e):
        idx = e.control.selected_index
        if idx == 0:
            main_container.content = chat_tab_content
        elif idx == 1:
            load_schedule()
            main_container.content = schedule_tab_content
        elif idx == 2:
            render_lists_overview()
            main_container.content = lists_main_container
        elif idx == 3:
            load_members()
            main_container.content = household_tab_content
        elif idx == 4:
            main_container.content = settings_tab_content
        page.update()

    page.navigation_bar = ft.NavigationBar(
        destinations=[
            ft.NavigationBarDestination(icon=ft.Icons.CHAT, label="Chat"),
            ft.NavigationBarDestination(icon=ft.Icons.CALENDAR_MONTH, label="Schedule"),
            ft.NavigationBarDestination(icon=ft.Icons.LIST_ALT, label="Lists"),
            ft.NavigationBarDestination(icon=ft.Icons.FAMILY_RESTROOM, label="Household"),
            ft.NavigationBarDestination(icon=ft.Icons.SETTINGS, label="Settings"),
        ],
        on_change=switch_tab
    )

    page.add(
        ft.Text("Haven", size=24, weight=ft.FontWeight.BOLD),
        main_container
    )
    
    # Load once at start
    load_schedule()
    render_lists_overview()
