from kivy.config import Config
Config.set('graphics', 'fullscreen','auto')

import requests
import sqlite3
import re
from kivy.app import App
from functools import partial
from kivy.metrics import sp
from threading import Thread
from kivy.clock import Clock
from kivy.uix.popup import Popup
from kivy.uix.spinner import Spinner
from kivy.core.window import Window
from kivy.uix.widget import Widget
from kivy.uix.label import Label
from kivy.core.clipboard import Clipboard
from kivy.core.text import LabelBase
from kivy.uix.gridlayout import GridLayout
from kivy.uix.textinput import TextInput
from kivy.graphics import Color, RoundedRectangle, Line,Rectangle
from kivy.uix.togglebutton import ToggleButton
from android.runnable import run_on_ui_thread
from kivy.uix.scrollview import ScrollView
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.graphics import Color,Line
from kivy.uix.image import Image
import arabic_reshaper
from bidi.algorithm import get_display
from kivy.animation import Animation
from jnius import autoclass

Window.clearcolor = (11/255,16/255,32/255,1)
Window.softinput_mode="below_target"
history=[]
currentchatid=None
currentmodel="llama3.1:8b"
urlt=""
lastmodel=""

@run_on_ui_thread
def set_system_bars(dt):
    PythonActivity = autoclass("org.kivy.android.PythonActivity")
    AndroidColor = autoclass("android.graphics.Color")

    activity = PythonActivity.mActivity
    window = activity.getWindow()

    window.setStatusBarColor(AndroidColor.parseColor("#0b1020"))
    window.setNavigationBarColor(AndroidColor.parseColor("#0b1020"))

LabelBase.register(
    name="Candara",
    fn_regular="Vazirmatn-Light.ttf",
    fn_bold="Vazirmatn-Bold.ttf",
    fn_italic="Vazirmatn-Thin.ttf",
    fn_bolditalic="Vazirmatn-ExtraBold.ttf"
)
LabelBase.register(
    name="roboto",
    fn_regular="Roboto-Regular.ttf",
)

def markdown(text):
    text=re.sub(r"\*\*(.*?)\*\*",r"[b]\1[/b]",text)
    text=re.sub(r"\*(.*?)\*",r"[i]\1[/i]",text)
    text=re.sub(r"```(.*?)```",
        r"\n\n\n[font=roboto]\1[/font]\n \n \n",
        text,
        flags=re.DOTALL
    )
    return text
    
def fix(text):
    if text is None:
        return ""
    reshaped=arabic_reshaper.reshape(str(text))
    return get_display(reshaped)

PythonActivity = autoclass("org.kivy.android.PythonActivity")
Rect = autoclass("android.graphics.Rect")

activity = PythonActivity.mActivity
view = activity.getWindow().getDecorView()

class Overlay(ButtonBehavior,Widget):
    def __init__(self,**kwargs):
        super().__init__(**kwargs)
        self.opacity=0
        self.disabled=True
        with self.canvas.before:
            Color(0,0,0,0.7)
            self.rect=Rectangle()
        def uprect(self,*args):
            self.rect.pos=self.pos
            self.rect.size=self.size
        self.bind(pos=uprect,size=uprect)
class Sidebar(ScrollView):
    def __init__(self,**kwargs):
        super().__init__(**kwargs)
        self.size_hint=(0.85,1)
        self.layout=BoxLayout(
            orientation="vertical",
            size_hint=(1,None),
            spacing=50
        )
        self.layout.bind(minimum_height=self.layout.setter("height"))

        def hide(instance,value):
            self.x=-self.width
        self.bind(size=hide)
        with self.canvas.before:
            Color(11/255,16/255,32/255,1)
            self.background=Rectangle()
            Color(0.5,0.5,0.5,1)
            self.borl=Line(width=1)
            self.bind(pos=self.updatebg,size=self.updatebg)
        self.layout.padding=(20,20,20,20)
        self.add_widget(self.layout)
    def updatebg(self,*args):
        self.background.pos=self.pos
        self.background.size=self.size
        self.borl.rounded_rectangle=(
            self.x,self.y,self.width,self.height,0
        )


class aianswer(Thread):
    def __init__(self,message,history,callback,command):
        super().__init__(daemon=True)
        self.message=message
        self.history=history
        self.callback=callback
        self.command=command
        messages=[
        {
        "role":"system",
        "content":self.command
        }
        ]

        for item in self.history:
            role,msg=item.split(":",1)
            messages.append({
                "role":role,
                "content":msg
            })

        messages.append({
        "role":"user",
        "content":self.message
        })
    def run(self):
        try:
            response=requests.post(
                urlt,
                json={
                    "model":currentmodel,
                    "messages":messages,
                    "stream":False
                }
            )
            answer=response.json()["message"]["content"]
            history.append(f"user:{self.message}")
            history.append(f"assistand:{answer}")
            conn=sqlite3.connect("database.db")
            cursor=conn.cursor()
            global currentchatid
            if(currentchatid==None):
                cursor.execute("""
                CREATE TABLE IF NOT EXISTS chats(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chatname TEXT,
                date DATETIME DEFAULT CURRENT_TIMESTAMP
                )
                """)
                conn.commit()
                cursor.execute("""
                INSERT INTO chats(
                chatname
                )
                VALUES(?)""",(self.message,))
                conn.commit()
                currentchatid=cursor.lastrowid
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS messages(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            forchat INTEGER,
            role TEXT,
            message TEXT,
            date DATETIME DEFAULT CURRENT_TIMESTAMP
            )
            """)
            cursor.execute("""
            INSERT INTO messages(forchat,role,message)
            VALUES(?,?,?)
            """,
            (currentchatid,"user",self.message))
            cursor.execute("""
            INSERT INTO messages(forchat,role,message)
            VALUES(?,?,?)
            """,
            (currentchatid,"assistant",answer))
            conn.commit()
            conn.close()
        except Exception as e:
            answer=f"Error:{e}"
        Clock.schedule_once(
            lambda dt:
            self.callback(answer)
        )
            
class screen(FloatLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)  
        main=GridLayout(rows=3) 
        self.add_widget(main)
        header=BoxLayout(size_hint_y=None,height=200)
        with header.canvas.after:
            Color(0.4,0.4,0.4,1)
            header.line=Line()
        messages=BoxLayout()
        bottom=BoxLayout(size_hint_y=None,height=200,orientation="horizontal",padding=10,spacing=10)
        main.add_widget(header)
        main.add_widget(messages)
        main.add_widget(bottom)
        with bottom.canvas.after:
            Color(0.4,0.4,0.4,1)
            bottom.line=Line()
        sidebb=Button(text="",size_hint=(None,None),width=140,height=180,
        background_normal="",
        background_disabled_normal="",
        background_color=(0,0,0,0))
        sideimage=Image(source="side2.png",size_hint=(None,None),size=(140, 140),allow_stretch=True,keep_ratio=True,pos=sidebb.pos)
        sidebb.add_widget(sideimage)
        header.add_widget(sidebb)
        overlay=Overlay()
        sidebar=Sidebar()
        sidebar.layout.orientation="vertical"
        def showtoast(message, duration=1):
            popup = Popup(
                title='',
                content=Label(text=message,font_size=48,font_name="Vazirmatn-Light.ttf"),
                size_hint=(0.5, 0.1),
                pos_hint={'center_x': 0.5, 'y': 0.05},
                background_color=(0.2, 0.2, 0.2, 0.9),
                auto_dismiss=False
            )
            popup.open()
            Clock.schedule_once(lambda dt: popup.dismiss(), duration)
        modelsettings = Button(
            text="Model Settings:",
            size_hint=(1, None),
            height=60,
            background_normal="",
            background_down="",
            background_color=(0, 0, 0, 0),
            color=(1, 1, 1, 1),
            halign="left",
            valign="middle",
            text_size=(0, None),
            font_name="calibri.ttf",
            font_size=50
        )
        modelswi=BoxLayout(orientation="vertical",spacing=20,size_hint=(0.9,None),height=500)
        with modelswi.canvas.before:
            Color(0.5,0.5,0.5,1)
            modelswi.border=Line(rounded_rectangle=(0,0,0,0,20),width=1.5)
            Color(30/255,42/255,86/255,0.8)
            modelswi.bg=RoundedRectangle(radius=[20])
        print(modelswi.pos,modelswi.size)
        modellabel=Label(text=("Choose the LLM model"),markup=True,font_size=45,width=messages.width,halign="left",valign="middle",size_hint_y=None,size_hint_x=1,text_size=(0,None),font_name="calibri.ttf")
        modellabel.bind(
            size=lambda instance, value:
            setattr(instance, "text_size", (instance.width - 40, instance.height))
        )
        modelswi.add_widget(modellabel)
        items=["gemma3:1b","gemma3:4b","llama3.1:8b","gemma3:12b","qwen3:14b"]
        for i in items:
            btn = ToggleButton(
                text=i,
                group='my_group',
                size_hint=(1, None),
                height=60,
                font_size=46,
                background_normal='',
                background_down="",
                text_size=(0,None),
                background_color=(0,0,0,0),
                halign="left",
                valign="center"
            )
            btn.bind(
                size=lambda instance, value:
                setattr(instance, "text_size", (instance.width - 40, instance.height))
            )
            def updatecolor(instance,state):
                global currentmodel
                if state=="down":
                    instance.background_color=(0.2,0.6,1,1)
                else:
                    instance.background_color=(0,0,0,0)
                currentmodel=instance.text
                print(currentmodel)
                modellabel.text=("Choose th LLM model")
            btn.bind(state=updatecolor)
            modelswi.add_widget(btn)
        def onchanged(instance,value):
            global urlt
            urlt=value
        urltextbar=TextInput(hint_text="Enter the URL...",background_color=(0,0,0,0),size_hint=(1,None),font_name="calibri.ttf",font_size=40,foreground_color=(1,1,1,1),cursor_color=(1,1,1,1),hint_text_color=(0.7,0.7,0.7,1),multiline=False,padding=[15,10,15,10],x=modelsettings.x,y=modelsettings.y+40)
        urltextbar.bind(text=onchanged)
        urltextbar.bind(
            size=lambda instance, value:
            setattr(instance, "text_size", (instance.width - 20, instance.height))
        )
        roleplayp=Button(
            text="Role play",
            size_hint=(1, None),
            height=60,
            background_normal="",
            background_down="",
            background_color=(0, 0, 0, 0),
            color=(1, 1, 1, 1),
            halign="left",
            valign="middle",
            text_size=(0, None),
            font_name="calibri.ttf",
            font_size=64,
            x=modelsettings.x,
            y=modelsettings.y+40
        )
        roleplayp.bind(
            size=lambda instance, value:
            setattr(instance, "text_size", (instance.width - 20, instance.height))
        )
        def showchat(chatid,instance):
            if self.firstmessage:
                self.mlist=ScrollView()
                self.mlist.opacity=1
                self.layout=BoxLayout(orientation="vertical",size_hint_y=None,spacing=20,padding=(10,10,10,10))
                self.layout.width=messages.width
                self.layout.bind(minimum_height=self.layout.setter("height"))
                self.mlist.add_widget(self.layout)
                messages.add_widget(self.mlist)
                messages.remove_widget(label)
                self.firstmessage=False
            global currentchatid
            currentchatid=chatid
            conn=sqlite3.connect("database.db")
            cursor=conn.cursor()
            cursor.execute("""
            SELECT message
            FROM messages
            WHERE forchat=?
            ORDER BY id
            """,(chatid,))
            messagesl=cursor.fetchall()
            conn.close()
            messlist=[]
            for i in messagesl:
                messlist.append(i[0])
            self.layout.clear_widgets()
            global history
            history=[]
            messcount=len(messlist)
            for i in range(0,messcount):
                texttt=messlist[i]
                if i%2==0:
                    messagehtml=markdown(messlist[i])
                    usermt=fix(messagehtml)
                    messagebubble=Label(markup=True,font_size=50,width=messages.width,halign="right",valign="middle",size_hint_y=None,size_hint_x=1,text_size=(self.layout.width-50,None),font_name="Candara")
                    messagebubble.text=(f"You:\n{messlist[i]}[ref=copy][color=bebebe]\ntap to copy[/color][/ref]")
                    def refpress(message,instance,ref):
                        if ref=="copy":
                            Clipboard.copy(texttt)
                            instance.text=f"You:\{usermt}[ref=copy][color=bebebe]\ncopied[/color][/ref]"
                    messagebubble.bind(on_ref_press=partial(refpress,texttt))
                    self.layout.add_widget(messagebubble)
                    messagebubble.bind(texture_size=lambda i,v:setattr(i,"height",v[1]+20))
                    history.append(f"user:{messlist[i]}")
                else:
                    self.answerl=Label(markup=True,font_size=50,width=messages.width,halign="left",valign="middle",size_hint_y=None,size_hint_x=1,text_size=(self.layout.width-50,None),font_name="Candara")
                    self.layout.add_widget(self.answerl)
                    self.answerl.bind(texture_size=lambda i,v:setattr(i,"height",v[1]+20))
                    bothtml=markdown(texttt)
                    botmt=fix(bothtml)
                    self.answerl.text=f"Carrot:\n{botmt}[ref=copy][color=bebebe]\ntap to copy[/color][/ref]"
                    def responserefp(response,instance,ref):
                        if ref=="copy":
                            Clipboard.copy(messlist[i])
                            instance.text=f"Carrot:\n{botmt}[ref=copy][color=bebebe]\ncopied[/color][/ref]"
                    self.answerl.bind(on_ref_press=partial(responserefp,texttt))
                    history.append(f"assistant:{messlist[i]}")
        cchl=Label(
            text="-Recent chats:",
            size_hint=(1, None),
            height=60,
            color=(1, 1, 1, 1),
            halign="left",
            valign="middle",
            text_size=(0, None),
            font_name="calibri.ttf",
            font_size=64,
        )
        cchl.bind(
            size=lambda instance, value:
            setattr(instance, "text_size", (instance.width - 20, instance.height))
        )
        sidebar.layout.add_widget(modelsettings)
        sidebar.layout.add_widget(modelswi)
        sidebar.layout.add_widget(urltextbar)
        sidebar.layout.add_widget(roleplayp)
        sidebar.layout.add_widget(cchl)
        conn=sqlite3.connect("database.db")
        cursor=conn.cursor()
        cursor.execute("""
        SELECT id,chatname,date FROM chats
        ORDER BY id
        """)
        chatslist=cursor.fetchall()
        i=0
        for i in chatslist:
            chatid=i[0]
            chatname=i[1]
            chatcrtime=i[2]
            print(f"chat {chatid}\n-------------\nchat id:{chatid}\nchat name={chatname}\nchat created at:{chatcrtime}")
            fichatname=fix(chatname)
            chatb=Button(text=f"\n{fichatname}\n[color=bebebe]{chatcrtime}[/color]\n",
            size_hint=(1, None),
            height=60,
            background_normal="",
            background_down="",
            background_color=(0, 0, 0, 0),
            color=(1, 1, 1, 1),
            halign="left",
            valign="middle",
            text_size=(500, None),
            font_name="Vazirmatn-Light.ttf",
            font_size=42,
            markup=True)
            ###chatb.bind(
            ###    size=lambda instance, value:
            ###    setattr(instance, "text_size", (instance.width - 20, instance.height))
            ###)
            chatb.bind(size=lambda i, v: setattr(i, "text_size", (i.width - 100, i.height+200)))
            chatb.bind(on_press=partial(showchat,chatid))
            sidebar.layout.add_widget(chatb)
        modelsettings.bind(
            size=lambda instance, value:
            setattr(instance, "text_size", (instance.width - 20, instance.height))
        )
        def hidesb(instance):
            Animation(opacity=0,d=0.25).start(overlay)
            self.remove_widget(overlay)
            Animation(x=-sidebar.width,d=0.5,t="out_quart").start(sidebar)
            Clock.schedule_once(lambda dt:setattr(overlay,"disabled",True),0.25)
            self.remove_widget(sidebar)
        overlay.bind(on_press=hidesb)
        def showsb(instance):
            self.add_widget(overlay)
            overlay.disabled=False
            Animation(opacity=1,d=0.2).start(overlay)
            self.add_widget(sidebar)
            Animation(x=0,d=0.5,t="out_quart").start(sidebar)
        sidebb.bind(on_press=showsb)
        logo=Label(text="PF-Carrot",color=(255/255,69/255,0/255,1),font_size=100,font_name="timesbd.ttf",bold=True)
        header.add_widget(logo)
        newcb=Button(text="",size_hint=(None,None),width=140,height=180,
        background_normal="",
        background_disabled_normal="",
        background_color=(0,0,0,0))
        newci=Image(source="newchat.png",size_hint=(None,None),size=(120, 120),allow_stretch=True,keep_ratio=True,pos=newcb.pos)
        newcb.add_widget(newci)
        header.add_widget(newcb)
        def newchattt(instance):
            if self.firstmessage==False:
                messages.remove_widget(self.mlist)
                messages.add_widget(label)
                self.firstmessage=True
            global history
            history=[]
            global currentchatid
            currentchatid=None
            showtoast("New Chat Opened")
        newcb.bind(on_press=newchattt)
        x=0
        label=Label(text="Welcome...How can I help u?",color=(255/255,255/255,255/255,1),font_size=60,font_name="georgia.ttf")
        messages.add_widget(label)
        textcontainer=FloatLayout(size_hint=(1,None),height=140)
        with textcontainer.canvas.before:
            Color(0.5,0.5,0.5,1)
            textcontainer.border=Line(rounded_rectangle=(0,0,0,0,20),width=1.5)
            Color(30/255,42/255,86/255,0.8)
            textcontainer.bg=RoundedRectangle(radius=[20])
        textbar=TextInput(hint_text="Type a message...",background_color=(0,0,0,0),foreground_color=(1,1,1,1),cursor_color=(1,1,1,1),hint_text_color=(0.7,0.7,0.7,1),multiline=False,padding=[15,10,15,10],size_hint=(1,1),font_size=36,font_name="Vazirmatn-Light.ttf")
        textcontainer.add_widget(textbar)
        def getkeyboardh():
            rect = Rect()
            view.getWindowVisibleDisplayFrame(rect)
            screenheight = view.getRootView().getHeight()
            keyboardheight = screenheight - rect.bottom
            return keyboardheight
        def onfocus(self,instance):
            keyboardheight=getkeyboardh()
            main.height=Window.height-keyboardheight
        textbar.bind(focus=onfocus)
        self.firstmessage=True
        def exctractm(answer):
            send.bind(on_press=sendmessage)
            send.remove_widget(answeringi)
            send.add_widget(sendimage)
            self.event.cancel()
            bothtml=markdown(answer)
            botmt=fix(bothtml)
            self.answerl.text=f"Carrot:\n{botmt}[ref=copy][color=bebebe]\ntap to copy[/color][/ref]"
            def responserefp(answert,instance,ref):
                if ref=="copy":
                    Clipboard.copy(answert)
                    instance.text=f"Carrot:\n{answert}[ref=copy][color=bebebe]\ncopied[/color][/ref]"
            self.answerl.bind(on_ref_press=partial(responserefp,answer))
        def sendmessage(instance):
            send.unbind(on_press=sendmessage)
            send.remove_widget(sendimage)
            send.add_widget(answeringi)
            if self.firstmessage:
                self.mlist=ScrollView()
                self.mlist.opacity=1
                self.layout=BoxLayout(orientation="vertical",size_hint_y=None,spacing=20,padding=(10,10,10,10))
                self.layout.width=messages.width
                self.layout.bind(minimum_height=self.layout.setter("height"))
                self.mlist.add_widget(self.layout)
                messages.add_widget(self.mlist)
                messages.remove_widget(label)
                self.firstmessage=False
            print(textbar.text)
            message=textbar.text
            right=AnchorLayout(anchor_x="right",anchor_y="center")
            umhtml=markdown(message)
            usermt=fix(umhtml)
            messagebubble=Label(markup=True,font_size=50,width=messages.width,halign="right",valign="middle",size_hint_y=None,size_hint_x=1,text_size=(self.layout.width-50,None),font_name="Candara")
            messagebubble.text=(f"You:\n{usermt}[ref=copy][color=bebebe]\ntap to copy[/color][/ref]")
            def refpress(message,instance,ref):
                if ref=="copy":
                    Clipboard.copy(message)
                    instance.text=f"You:\n{usermt}[ref=copy][color=bebebe]\ncopied[/color][/ref]"
            messagebubble.bind(on_ref_press=partial(refpress,message))
            self.layout.add_widget(messagebubble)
            messagebubble.bind(texture_size=lambda i,v:setattr(i,"height",v[1]+20))
            textbar.text=""
            global history
            self.answerl=Label(markup=True,font_size=50,width=messages.width,halign="left",valign="middle",size_hint_y=None,size_hint_x=1,text_size=(self.layout.width-50,None),font_name="Candara")
            self.layout.add_widget(self.answerl)
            self.answerl.bind(texture_size=lambda i,v:setattr(i,"height",v[1]+20))
            self.dots=0
            def thinking(dt):
                self.answerl.text="Carrot is thinking"+"."*self.dots
                self.dots+=1
                if self.dots>3:
                    self.dots=0
            self.event=Clock.schedule_interval(thinking,0.3)
            command=f"""You are an AI chatbot named Carrot.be friendly and natural
                            """
            aianswer(message,history,exctractm,command).start()
        answeringiii=Image(source="answering.png",size_hint=(None,None),size=(70, 70),allow_stretch=True,keep_ratio=True)
        def rewritefinish(newp):
            send.bind(on_press=sendmessage)
            rewriteb.bind(on_press=rewrite)
            rewriteb.remove_widget(answeringiii)
            rewriteb.add_widget(rewritei)
            textbar.text=newp
            print(newp)
            global currentmodel
            currentmodel=lastmodel
        def rewrite(self):
            send.unbind(on_press=sendmessage)
            rewriteb.unbind(on_press=rewrite)
            rewriteb.remove_widget(rewritei)
            rewriteb.add_widget(answeringiii)
            global currentmodel
            lastmodel=currentmodel
            currentmodel="gemma3:4b"
            rag=("""
            You are an AI Prompt Designer. Rewrite the user's request into a clear, professional, and optimized prompt while preserving its intent.

            Rules:
            - Do not answer the request.
            - Respond with only the final prompt.
            """)
            aianswer(textbar.text,None,rewritefinish,rag).start()
        rewriteb=Button(font_name="Candara.ttf",font_size=22,size_hint=(None,None),size=(65,65),background_normal="",background_color=(0,0,0,0))
        rewriteb.bind(on_press=rewrite)
        rewritei=Image(source="download.png",size=(75,75))
        rewriteb.add_widget(rewritei)
        showing=False
        def showorhide(instance,value):
            nonlocal showing
            if len(value)>70:
                if(showing==False):
                    bottom.add_widget(rewriteb,index=1)
                    showing=True
                else:
                    return
            else:
                if showing:
                    bottom.remove_widget(rewriteb)
                    showing=False
                else:
                    return

        textbar.bind(text=showorhide)
        send=Button(size_hint=(None,None),width=140,height=140,
        background_normal="",
        background_disabled_normal="",
        background_color=(0,0,0,0))
        sendimage=Image(source="send.png",size_hint=(None,None),size=(140, 140),allow_stretch=True,keep_ratio=True,pos=send.pos)
        answeringi=Image(source="answering.png",size_hint=(None,None),size=(70, 70),allow_stretch=True,keep_ratio=True,pos=send.pos)
        send.add_widget(sendimage)
        bottom.add_widget(textcontainer)
        bottom.add_widget(send)

        def updatehl(instance,value):
            x,y=instance.pos
            w,h=instance.size
            instance.line.points=[x,y,x+w,y]
        header.bind(pos=updatehl,size=updatehl)
        def updateb(instance, value):
            x,y=instance.pos
            w,h=instance.size
            instance.line.points=[x,y+h,x+w,y+h]
        bottom.bind(pos=updateb,size=updateb)
        def centerimage(instance, value):
            sendimage.center = instance.center
            answeringi.center=instance.center
            
        send.bind(pos=centerimage, size=centerimage)
        def centerimage2(instance,value):
            sideimage.center=instance.center
        sidebb.bind(pos=centerimage2,size=centerimage2)

        def centerimage3(instance,value):
            newci.center=instance.center
        newcb.bind(pos=centerimage3,size=centerimage3)

        def centerimage4(instance,value):
            rewritei.center=instance.center
            answeringiii.center=instance.center
        rewriteb.bind(pos=centerimage4,size=centerimage4)

        def updatet(instance, value):
            textcontainer.bg.pos = textcontainer.pos
            textcontainer.bg.size = textcontainer.size
            textcontainer.border.rounded_rectangle = (
                textcontainer.x,
                textcontainer.y,
                textcontainer.width,
                textcontainer.height,
                20
            )

        textcontainer.bind(pos=updatet, size=updatet)
        send.bind(on_press=sendmessage)
        def updatehj(instance,value):
            modelswi.bg.pos = modelswi.pos
            modelswi.bg.size = modelswi.size
            modelswi.border.rounded_rectangle = (
                modelswi.x,
                modelswi.y,
                modelswi.width,
                modelswi.height,
                20
            ) 
        modelswi.bind(pos=updatehj, size=updatehj) 
from kivy.clock import Clock

class pfcApp(App):
    def build(self):
        return screen()
    def on_start(self):
        Clock.schedule_once(set_system_bars, 0)


   

pfcApp().run()
