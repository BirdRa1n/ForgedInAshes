"""D12: writes the windows of the mod (Machine Panel, Recipe Picker, Settings, Network Panel, Production Guide) into
Config/XUi_InGame/windows.xml and their window groups into xui.xml. Controllers: src/FerroEngrenagem/FeUi.cs.
No <textfield>: one in a mod window broke XUi.Cleanup when leaving the world (2026-11-24 log).

Usage: python tools/gen_ui.py
"""
import os, re
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
P = 'Mods/FerroEngrenagem/Config/XUi_InGame/windows.xml'
X = 'Mods/FerroEngrenagem/Config/XUi_InGame/xui.xml'
BEGIN = '<!-- BEGIN D12 windows (tools/gen_ui.py, controllers in FeUi.cs) -->'
END = '<!-- END D12 windows -->'

BTN = ('<button depth="3" name="{id}" pos="{x},{y}" width="{w}" height="40" sprite="menu_empty" defaultcolor="[mediumGrey]" '
       'hoversprite="ui_game_select_row" hovercolor="[white]" type="sliced" hoverscale="1.0"/>\n'
       '\t\t\t\t<label depth="4" pos="{x},{ly}" width="{w}" height="32" justify="center" text="{text}" font_size="24" />')


def btn(id, x, y, w, text):
    return '\t\t\t\t' + BTN.format(id=id, x=x, y=y, w=w, ly=y - 6, text=text)


def frame(name, ctrl, w, h, icon, inner):
    return f'''		<window name="{name}" width="{w}" height="{h}" pos="{-w // 2},{h // 2}" anchor="Center" depth="15" cursor_area="true"
		        controller="FerroEngrenagem.{ctrl}, FerroEngrenagem">
			<rect name="header" height="43" depth="1">
				<headerbg />
				<sprite depth="2" name="windowIcon" style="icon32px" pos="4,-5" sprite="{icon}"/>
				<label style="header.name" text="{{fetitle}}" width="{w - 100}" />
			</rect>
			<rect name="content" pos="0,-46" height="{h - 46}" depth="1">
				<sprite depth="8" name="backgroundMain" sprite="menu_empty3px" pos="0,0" width="{w}" color="[black]" type="sliced" fillcenter="false" />
				<sprite color="[darkGrey]" type="sliced" />
{inner}
			</rect>
		</window>'''


def bar(y, buttons, w):
    # buttons: list of (id, text); spread across the width
    n = len(buttons)
    bw = min(220, (w - 16 - (n - 1) * 8) // n)
    out = []
    for i, (id, text) in enumerate(buttons):
        out.append(btn(id, 8 + i * (bw + 8), y, bw, text))
    return '\n'.join(out)


def rows(prefix_btn, prefix_bind, n, y0, w, step=44):
    out = []
    for i in range(n):
        y = y0 - i * step
        out.append(f'\t\t\t\t<button depth="3" name="{prefix_btn}{i}" pos="8,{y}" width="{w - 16}" height="{step - 4}" sprite="menu_empty" '
                   f'defaultcolor="[darkGrey]" hoversprite="ui_game_select_row" hovercolor="[white]" type="sliced" hoverscale="1.0" visible="{{{prefix_bind}v{i}}}"/>')
        out.append(f'\t\t\t\t<sprite depth="5" atlas="ItemIconAtlas" sprite="{{{prefix_bind}i{i}}}" pos="14,{y - 2}" size="36,36" foregroundlayer="true" visible="{{{prefix_bind}v{i}}}"/>')
        out.append(f'\t\t\t\t<label depth="5" pos="58,{y - 8}" width="{w - 80}" height="30" text="{{{prefix_bind}t{i}}}" font_size="22" />')
    return '\n'.join(out)


W1, H1 = 1100, 700
machine = frame('feMachine', 'FeMachine', W1, H1, 'ui_game_symbol_wrench',
    f'\t\t\t\t<label depth="3" pos="12,-10" text="{{febody}}" width="{W1 - 24}" height="{H1 - 140}" font_size="24" />\n'
    + bar(-(H1 - 46) + 52, [('feMBtnPick', 'Receita'), ('feMBtnPut', 'Pôr item da mão'), ('feMBtnTake', 'Retirar produtos'),
                           ('feMBtnOnOff', '{feonoff}'), ('feMBtnClose', 'Fechar')], W1))

W2, H2 = 1100, 640
picker = frame('fePicker', 'FePicker', W2, H2, 'ui_game_symbol_book',
    rows('fePRow', 'fep', 10, -8, W2) + '\n'
    + f'\t\t\t\t<label depth="4" pos="{W2 // 2 - 100},{-(H2 - 46) + 46}" width="200" height="32" justify="center" text="{{fepage}}" font_size="24" />\n'
    + btn('fePPrev', 8, -(H2 - 46) + 52, 180, '&lt;&lt;') + '\n'
    + btn('fePNext', W2 - 188 - 196, -(H2 - 46) + 52, 180, '&gt;&gt;') + '\n'
    + btn('fePClose', W2 - 188, -(H2 - 46) + 52, 180, 'Fechar'))

W3, H3 = 900, 520
config = frame('feConfig', 'FeConfig', W3, H3, 'ui_game_symbol_tool',
    f'\t\t\t\t<label depth="3" pos="12,-10" text="{{febody}}" width="{W3 - 24}" height="{H3 - 140}" font_size="24" />\n'
    + bar(-(H3 - 46) + 52, [('feCMinus', '-'), ('feCPlus', '+'), ('feCMode', 'Modo'), ('feCHand', 'Item da mão'), ('feCClose', 'Fechar')], W3))

W4, H4 = 1100, 700
network = frame('feNetwork', 'FeNetwork', W4, H4, 'ui_game_symbol_electric_power',
    f'\t\t\t\t<label depth="3" pos="12,-10" text="{{febody}}" width="{W4 - 24}" height="{H4 - 140}" font_size="22" />\n'
    + btn('feNClose', W4 - 188, -(H4 - 46) + 52, 180, 'Fechar'))

W5, H5 = 1200, 860
guide = frame('feGuide', 'FeGuide', W5, H5, 'ui_game_symbol_book',
    f'\t\t\t\t<label depth="3" pos="12,-12" width="140" height="30" text="Letra:" font_size="24" />\n'
    + btn('feGLetterBack', 120, -6, 60, '&lt;') + '\n'
    + f'\t\t\t\t<label depth="4" pos="186,-12" width="80" height="30" justify="center" text="{{feletter}}" font_size="26" />\n'
    + btn('feGLetter', 270, -6, 60, '&gt;') + '\n'
    f'\t\t\t\t<label depth="3" pos="12,-48" text="{{febody}}" width="{W5 - 24}" height="200" font_size="22" />\n'
    + rows('feGRow', 'feg', 12, -256, W5) + '\n'
    + f'\t\t\t\t<label depth="4" pos="{W5 // 2 - 100},{-(H5 - 46) + 46}" width="200" height="32" justify="center" text="{{fepage}}" font_size="24" />\n'
    + btn('feGPrev', 8, -(H5 - 46) + 52, 150, '&lt;&lt;') + '\n'
    + btn('feGIndex', 166, -(H5 - 46) + 52, 150, 'Índice') + '\n'
    + btn('feGHand', 324, -(H5 - 46) + 52, 170, 'Item da mão') + '\n'
    + btn('feGBack', W5 - 158 - 158 - 158 - 30, -(H5 - 46) + 52, 150, 'Voltar') + '\n'
    + btn('feGNext', W5 - 158 - 158, -(H5 - 46) + 52, 150, '&gt;&gt;') + '\n'
    + btn('feGClose', W5 - 158, -(H5 - 46) + 52, 150, 'Fechar'))

block = f'''	{BEGIN}
	<append xpath="/windows">
{machine}
{picker}
{config}
{network}
{guide}
	</append>
	{END}'''
s = open(P, encoding='utf-8').read()
if BEGIN in s:
    s = re.sub(re.escape('\t' + BEGIN) + '.*?' + re.escape(END), lambda m: block, s, flags=re.S)
else:
    s = s.replace('</configs>', block + '\n</configs>')
open(P, 'w', encoding='utf-8', newline='').write(s)

groups = ''.join(f'\t\t<window_group name="{n}" defaultselected="{d}">\n\t\t\t<window name="{n}" />\n\t\t</window_group>\n'
                 for n, d in [('feMachine', 'feMBtnClose'), ('fePicker', 'fePClose'), ('feConfig', 'feCClose'),
                              ('feNetwork', 'feNClose'), ('feGuide', 'feGClose')])
xb = f'\t{BEGIN}\n\t<append xpath="/xui">\n{groups}\t</append>\n\t{END}'
x = open(X, encoding='utf-8').read()
if BEGIN in x:
    x = re.sub(re.escape('\t' + BEGIN) + '.*?' + re.escape(END), lambda m: xb, x, flags=re.S)
else:
    x = x.replace('</configs>', xb + '\n</configs>')
open(X, 'w', encoding='utf-8', newline='').write(x)
print('ok')
