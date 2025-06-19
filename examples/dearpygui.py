import dearpygui.dearpygui as dpg

# Setup context
dpg.create_context()
dpg.create_viewport(title='Dear PyGui IDE', width=1600, height=900)
dpg.setup_dearpygui()

with dpg.font_registry():
    print("add font")
    default_font = dpg.add_font("pymfd/backend/fonts/consolas.ttf", 16)

node_editor = None
active_tab = "NodeEditorTab"
nodes = []
links = []

def tab_changed(sender, app_data):
    global active_tab
    print(sender, app_data)
    active_tab = dpg.get_item_alias(app_data)
    print(active_tab)

# callback runs when user attempts to connect attributes
def link_callback(sender, app_data):
    # app_data -> (link_id1, link_id2)
    link = dpg.add_node_link(app_data[0], app_data[1], parent=sender)
    links.append(link)
    print(f"link sender:{sender} app_data:{app_data} link:{link}")

# callback runs when user attempts to disconnect attributes
def delink_callback(sender, app_data):
    # app_data -> link_id
    links.remove(app_data)
    dpg.delete_item(app_data)
    print(f"delink sender:{sender} app_data:{app_data}")

# Delete nodes/links
def delete_selected(sender, app_data):
    if active_tab != "NodeEditorTab":
        return

    for node in dpg.get_selected_nodes(node_editor):
        node_name = dpg.get_item_alias(node)
        nodes.remove(node_name)
        dpg.delete_item(node)
        print(f"remove node sender:{sender} app_data:{app_data} node:{node}/{node_name}")
    for link in dpg.get_selected_links(node_editor):
        delink_callback(node_editor, link)

def add_node(sender, app_data):
    if active_tab != "NodeEditorTab":
        return

    node_tag = f"node{len(nodes)}"
    with dpg.node(parent=node_editor, label=f"Node {len(nodes)}", tag=node_tag) as node:
        with dpg.node_attribute(attribute_type=dpg.mvNode_Attr_Input):
            dpg.add_input_text(default_value="short", width=120)
        with dpg.node_attribute(attribute_type=dpg.mvNode_Attr_Output):
            dpg.add_input_text(default_value="short", width=120)
        nodes.append(node)
        print(f"add node sender:{sender} app_data:{app_data} node:{node}/{node_tag}")

# Key press handlers
with dpg.handler_registry():
    print("register keys")
    dpg.add_key_press_handler(key=dpg.mvKey_Delete, callback=delete_selected)
    dpg.add_key_press_handler(key=dpg.mvKey_Back, callback=delete_selected)
    dpg.add_key_press_handler(key=dpg.mvKey_Insert, callback=add_node)

def run():
    # Main app layout
    with dpg.window(tag="PrimaryWindow", no_close=True, no_collapse=True, no_move=True, no_resize=True):
        with dpg.group(horizontal=False):
            with dpg.child_window(tag="TopPane", autosize_x=True):
                with dpg.group(horizontal=True):
                    # Left Pane
                    with dpg.child_window(tag="LeftPane", autosize_y=True):
                        with dpg.tab_bar(callback=tab_changed, tag="TabBar"):

                            with dpg.tab(label="Node Editor", tag="NodeEditorTab"):
                                global node_editor
                                with dpg.node_editor(tag="NodeEditor", callback=link_callback, delink_callback=delink_callback, minimap=True, minimap_location=3) as node_editor:
                                    pass

                            with dpg.tab(label="Text Editor", tag="TextEditorTab"):
                                dpg.add_input_text(multiline=True, tag="TextEditor", default_value="# Python code\nprint('Hello')",
                                                height=-1, width=-1, tab_input=True)

                    # Right Pane
                    with dpg.child_window(tag="RightPane", autosize_y=True):
                        dpg.add_text("HTML Viewer")
                        dpg.add_text("[Embed HTML here via browser plugin or preview pane]")

            # Bottom Pane
            with dpg.child_window(tag="ConsolePane", autosize_x=True):
                dpg.add_input_text(multiline=True, readonly=True, tag="ConsoleLog", default_value="Console Output\n",
                                    height=-1, width=-1)

    def update_layout():
        """Dynamically resize top and bottom sections based on viewport size."""
        full_width = dpg.get_viewport_client_width()
        full_height = dpg.get_viewport_client_height()

        console_height = 200
        top_height = full_height - console_height

        # Resize horizontal panes
        dpg.configure_item("LeftPane", width=full_width // 2)
        dpg.configure_item("RightPane", width=full_width // 2)

        # Resize bottom console
        dpg.configure_item("TopPane", height=top_height)
        dpg.configure_item("ConsolePane", width=full_width, height=console_height)

    # Hook: run once after viewport is shown
    def on_viewport_resize(sender, app_data):
        update_layout()

    # Set up resize hook
    dpg.set_viewport_resize_callback(on_viewport_resize)
    
    # Final setup
    dpg.bind_font(default_font)
    dpg.set_primary_window("PrimaryWindow", True)
    dpg.show_viewport()
    update_layout()
    dpg.start_dearpygui()
    dpg.destroy_context()



run()































# # Right-click context menu
# def add_node_callback(sender, app_data):
#     with dpg.node(label="Node", parent="NodeEditor") as node_id:
#         dpg.add_node_attribute(label="Attribute")
#         # dpg.bind_item_handler_registry(node_id, "NodeHandlers")
#         # nodes.append(node_id)





