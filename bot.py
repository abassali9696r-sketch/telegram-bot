import os, glob, json, asyncio, random
for f in glob.glob("*.session*")+glob.glob("*.journal"):
 try: os.remove(f)
 except: pass
from telethon import Button, TelegramClient, errors, events
from telethon.sessions import StringSession

BOT_TOKEN=os.getenv("BOT_TOKEN","8403946923:AAGyPe-BLcbIj49UKJsM_xDOMeTKuku_l1o")
API_ID=2040
API_HASH="b18441a1ed607e10a3999b91231343e5"
DATA_FILE="users_data.json"

data=json.load(open(DATA_FILE,"r",encoding="utf-8")) if os.path.exists(DATA_FILE) else {}
def save_data():
 with open(DATA_FILE,"w",encoding="utf-8") as f:
  json.dump(data,f,ensure_ascii=False,indent=2)

bot=TelegramClient(StringSession(),API_ID,API_HASH)
login_states={};user_states={};active_tasks={}

async def send_to_group(uid,text):
 ud=data.get(uid)
 if not ud or not ud.get("session_string") or not ud.get("group_link"): return
 try:
  cl=TelegramClient(StringSession(ud["session_string"]),API_ID,API_HASH)
  await cl.connect()
  lines=text.splitlines() or [text]
  for i in range(0,len(lines),100):
   chunk="\n".join(lines[i:i+100])
   for j in range(0,len(chunk),4096):
    await cl.send_message(ud["group_link"],chunk[j:j+4096])
    await asyncio.sleep(2)
  await cl.disconnect()
 except errors.FloodWaitError as e:
  await asyncio.sleep(e.seconds+2)
 except Exception as e:
  print(e)

async def publishing_loop(uid):
 while data.get(uid,{}).get("is_running"):
  ud=data.get(uid)
  if not ud or not ud.get("vocabularies") or not ud.get("group_link"):
   await asyncio.sleep(5)
   continue
  for _ in range(50):
   if not data.get(uid,{}).get("is_running"): break
   vocab=random.choice(ud["vocabularies"])
   await send_to_group(uid,vocab)
  for _ in range(300):
   if not data.get(uid,{}).get("is_running"): break
   await asyncio.sleep(1)

async def show_panel(event,uid):
 ud=data.get(str(uid),{})
 txt=f"🎛 لوحة تحكم بوت النشر\n\nحالة: {'🟢 يعمل كل 5 دقايق' if ud.get('is_running') else '🔴 متوقف'}\n📚 المفردات: {len(ud.get('vocabularies',[]))}\n🔗 الجروب: {ud.get('group_link') or 'مو محدد'}\n\nالاعدادات: 50 كليشة / 2 ثانية / 100 سطر"
 btns=[
 [Button.inline("⏹ ايقاف" if ud.get('is_running') else "▶️ بدء النشر",b"toggle")],
 [Button.inline("➕ اضافة",b"add"),Button.inline("🗑 مسح",b"del")],
 [Button.inline("🔀 خلط الاماكن",b"shuffle"),Button.inline("↕️ نقل مفردة",b"move")],
 [Button.inline("🔗 الجروب",b"group"),Button.inline("📋 عرض",b"list")]
 ]
 if hasattr(event,"edit"): await event.edit(txt,buttons=btns)
 else: await event.respond(txt,buttons=btns)

@bot.on(events.NewMessage(pattern="/start"))
async def start_h(event):
 if not event.is_private: return
 uid=str(event.sender_id)
 if uid not in data:
  data[uid]={"session_string":None,"vocabularies":[],"group_link":None,"is_running":False}
  save_data()
 if data[uid].get("session_string"): await show_panel(event,uid)
 else:
  login_states[uid]={"step":"phone"};await event.respond("🔑 ارسل رقمك الاسباني مع رمز البلد +34...")

@bot.on(events.NewMessage())
async def msg_h(event):
 if not event.is_private or event.text.startswith("/"): return
 uid=str(event.sender_id); ud=data.get(uid,{})
 if uid in login_states:
  st=login_states[uid]
  if st["step"]=="phone":
   try:
    cl=TelegramClient(StringSession(),API_ID,API_HASH);await cl.connect();s=await cl.send_code_request(event.text.strip())
    st.update({"client":cl,"phone":event.text.strip(),"hash":s.phone_code_hash,"step":"code"});await event.respond("📩 ارسل كود التحقق:")
   except Exception as e: await event.respond(f"❌ {e}");login_states.pop(uid,None)
  elif st["step"]=="code":
   try:
    await st["client"].sign_in(st["phone"],event.text.strip(),phone_code_hash=st["hash"])
    ud["session_string"]=st["client"].session.save();save_data();await st["client"].disconnect();login_states.pop(uid,None)
    await event.respond("✅ تم الدخول!");await show_panel(event,uid)
   except errors.SessionPasswordNeededError: st["step"]="pass";await event.respond("🔒 ارسل باسورد التحقق بخطوتين:")
   except Exception as e: await event.respond(f"❌ {e}")
  elif st["step"]=="pass":
   try:
    await st["client"].sign_in(password=event.text.strip());ud["session_string"]=st["client"].session.save();save_data();await st["client"].disconnect();login_states.pop(uid,None);await event.respond("✅ تم!");await show_panel(event,uid)
   except Exception as e: await event.respond(f"❌ {e}")
  return
 sa=user_states.get(uid)
 if sa=="group": ud["group_link"]=event.text.strip();user_states.pop(uid,None);save_data();await show_panel(event,uid)
 elif sa=="add": ud["vocabularies"].append(event.text);save_data();user_states.pop(uid,None);await event.respond(f"✅ تمت الاضافة - عندك {len(ud['vocabularies'])}");await show_panel(event,uid)
 elif sa=="del":
  if event.text.strip() in ud["vocabularies"]: ud["vocabularies"].remove(event.text.strip());save_data();await event.respond("✅ تم المسح")
  else: await event.respond("❌ ما موجود")
  user_states.pop(uid,None);await show_panel(event,uid)
 elif sa=="move":
  try:
   a,b=map(int,event.text.split());a-=1;b-=1
   item=ud["vocabularies"].pop(a);ud["vocabularies"].insert(b,item);save_data()
   await event.respond(f"✅ نقلت من {a+1} الى {b+1}");user_states.pop(uid,None);await show_panel(event,uid)
  except: await event.respond("❌ ارسل مثل: 1 5")

@bot.on(events.CallbackQuery())
async def cb_h(event):
 uid=str(event.sender_id); ud=data.get(uid,{}); d=event.data.decode()
 if d=="toggle":
  if not ud.get("is_running"):
   if not ud.get("group_link") or not ud.get("vocabularies"): await event.answer("حدد الجروب وضيف كليشات اول!",alert=True);return
   ud["is_running"]=True;save_data();active_tasks[uid]=asyncio.create_task(publishing_loop(uid));await event.answer("بدأ النشر كل 5 دقايق - 50 كليشة")
  else:
   ud["is_running"]=False;save_data()
   if uid in active_tasks: active_tasks[uid].cancel()
   await event.answer("توقف النشر")
  await show_panel(event,uid)
 elif d=="shuffle": random.shuffle(ud["vocabularies"]);save_data();await event.answer("🔀 تم خلط اماكن المفردات!");await show_panel(event,uid)
 elif d=="move": user_states[uid]="move";await event.edit("↕️ ارسل رقمين: القديم والجديد\nمثال: 1 5")
 elif d=="group": user_states[uid]="group";await event.edit("🔗 ارسل رابط الجروب:")
 elif d=="add": user_states[uid]="add";await event.edit("➕ ارسل الكليشة (100 سطر او اكثر):")
 elif d=="del": user_states[uid]="del";await event.edit("🗑 ارسل نص الكليشة للمسح:")
 elif d=="list":
  txt="\n\n---\n\n".join(ud.get("vocabularies",[])[:3]) or "فارغ"
  await event.edit(f"📋 اول 3 كليشات:\n{txt[:3500]}",buttons=[[Button.inline("🔙 رجوع",b"back")]])
 elif d=="back": await show_panel(event,uid)

async def main():
 print("Bot starting...");await bot.start(bot_token=BOT_TOKEN)
 for uid,ud in data.items():
  if ud.get("is_running"): ud["is_running"]=False;save_data()
 print("Bot started!");await bot.run_until_disconnected()
asyncio.run(main())
