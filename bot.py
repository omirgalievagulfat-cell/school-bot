import asyncio
import sqlite3
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from apscheduler.schedulers.asyncio import AsyncIOScheduler

TOKEN = "9144113832:AAE4rbza502Iz2ZZi2AdMUhEtd3x8vConeY"

bot = Bot(token=TOKEN)
dp = Dispatcher()
scheduler = AsyncIOScheduler(timezone="Asia/Almaty")

def init_db():
    conn = sqlite3.connect("school_bot.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS teachers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER,
            full_name TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS coordinators (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER,
            full_name TEXT,
            flow_name TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS advisors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER,
            full_name TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS schedules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            teacher_id INTEGER,
            flow_name TEXT,
            subject TEXT,
            lesson_time TEXT
        )
    """)
    conn.commit()
    conn.close()

init_db()

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    conn = sqlite3.connect("school_bot.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id, full_name FROM teachers")
    teachers = cursor.fetchall()
    
    cursor.execute("SELECT id, full_name, flow_name FROM coordinators")
    coordinators = cursor.fetchall()

    cursor.execute("SELECT id, full_name FROM advisors")
    advisors = cursor.fetchall()
    conn.close()

    builder = InlineKeyboardBuilder()
    for t_id, name in teachers:
        builder.button(text=f"👨‍🏫 Мұғалім: {name}", callback_data=f"select_teacher_{t_id}")
    for c_id, name, flow in coordinators:
        builder.button(text=f"📋 Координатор ({flow}): {name}", callback_data=f"select_coord_{c_id}")
    for a_id, name in advisors:
        builder.button(text=f"🎓 Эдвайзер: {name}", callback_data=f"select_advisor_{a_id}")
    
    builder.adjust(1)

    if not teachers and not coordinators and not advisors:
        await message.answer("Жүйеде қолданушылар жоқ.")
        return

    await message.answer("Сәлеметсіз бе! Тізімнен өз аты-жөніңізді таңдаңыз:", reply_markup=builder.as_markup())

@dp.callback_query(lambda c: c.data.startswith("select_teacher_"))
async def process_teacher_selection(callback: types.CallbackQuery):
    teacher_id = int(callback.data.split("_")[2])
    
    conn = sqlite3.connect("school_bot.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE coordinators SET telegram_id = NULL WHERE telegram_id = ?", (callback.from_user.id,))
    cursor.execute("UPDATE advisors SET telegram_id = NULL WHERE telegram_id = ?", (callback.from_user.id,))
    cursor.execute("UPDATE teachers SET telegram_id = ? WHERE id = ?", (callback.from_user.id, teacher_id))
    cursor.execute("SELECT full_name FROM teachers WHERE id = ?", (teacher_id,))
    t_name = cursor.fetchone()[0]
    conn.commit()
    conn.close()

    await callback.message.edit_text(
        f"✅ Құттықтаймын, {t_name}! Мұғалім ретінде сәтті тіркелдіңіз.\n\n"
        "Сабақтарыңызды көру үшін: `/my_lessons` басыңыз."
    )
    await callback.answer()

@dp.callback_query(lambda c: c.data.startswith("select_coord_"))
async def process_coord_selection(callback: types.CallbackQuery):
    coord_id = int(callback.data.split("_")[2])
    
    conn = sqlite3.connect("school_bot.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE teachers SET telegram_id = NULL WHERE telegram_id = ?", (callback.from_user.id,))
    cursor.execute("UPDATE advisors SET telegram_id = NULL WHERE telegram_id = ?", (callback.from_user.id,))
    cursor.execute("UPDATE coordinators SET telegram_id = ? WHERE id = ?", (callback.from_user.id, coord_id))
    cursor.execute("SELECT full_name, flow_name FROM coordinators WHERE id = ?", (coord_id,))
    c_name, flow = cursor.fetchone()
    conn.commit()
    conn.close()

    await callback.message.edit_text(
        f"✅ Құттықтаймын, {c_name}! ({flow} потогының координаторы) сәтті тіркелдіңіз.\n\n"
        "Потогыңыздың сабақтарын көру үшін: `/my_lessons` басыңыз."
    )
    await callback.answer()

@dp.callback_query(lambda c: c.data.startswith("select_advisor_"))
async def process_advisor_selection(callback: types.CallbackQuery):
    advisor_id = int(callback.data.split("_")[2])
    
    conn = sqlite3.connect("school_bot.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE teachers SET telegram_id = NULL WHERE telegram_id = ?", (callback.from_user.id,))
    cursor.execute("UPDATE coordinators SET telegram_id = NULL WHERE telegram_id = ?", (callback.from_user.id,))
    cursor.execute("UPDATE advisors SET telegram_id = ? WHERE id = ?", (callback.from_user.id, advisor_id))
    cursor.execute("SELECT full_name FROM advisors WHERE id = ?", (advisor_id,))
    a_name = cursor.fetchone()[0]
    conn.commit()
    conn.close()

    await callback.message.edit_text(
        f"✅ Құттықтаймын, {a_name}! (Академиялық эдвайзер) сәтті тіркелдіңіз.\n\n"
        "Барлық ағымдардың кестесін көру үшін: `/my_lessons` басыңыз."
    )
    await callback.answer()

@dp.message(Command("add_teacher"))
async def add_teacher(message: types.Message):
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("Мына үлгіні қолданыңыз: `/add_teacher Өмірсеріков Бахтияр`")
        return
    
    name = parts[1]
    conn = sqlite3.connect("school_bot.db")
    cursor = conn.cursor()
    cursor.execute("INSERT INTO teachers (full_name) VALUES (?)", (name,))
    conn.commit()
    conn.close()
    
    await message.answer(f"✅ Мұғалім сәтті қосылды: {name}")

@dp.message(Command("add_coordinator"))
async def add_coordinator(message: types.Message):
    try:
        content = message.text.replace("/add_coordinator", "", 1).strip()
        parts = [p.strip() for p in content.split("|")]
        if len(parts) < 2:
            await message.answer("❌ Қате пішім! Үлгі:\n`/add_coordinator Камшат | ГЕО-01`")
            return
        
        name, flow = parts[0], parts[1]
        conn = sqlite3.connect("school_bot.db")
        cursor = conn.cursor()
        cursor.execute("INSERT INTO coordinators (full_name, flow_name) VALUES (?, ?)", (name, flow))
        conn.commit()
        conn.close()
        
        await message.answer(f"✅ Координатор қосылды!\n👤 Аты: {name}\n📌 Потогы: {flow}")
    except Exception as e:
        await message.answer(f"❌ Қате: {e}")

@dp.message(Command("add_advisor"))
async def add_advisor(message: types.Message):
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("Мына үлгіні қолданыңыз: `/add_advisor Гүлфат`")
        return
    
    name = parts[1]
    conn = sqlite3.connect("school_bot.db")
    cursor = conn.cursor()
    cursor.execute("INSERT INTO advisors (full_name) VALUES (?)", (name,))
    conn.commit()
    conn.close()
    
    await message.answer(f"✅ Академиялық эдвайзер сәтті қосылды: {name}")

@dp.message(Command("add_lesson"))
async def add_lesson_admin(message: types.Message):
    try:
        content = message.text.replace("/add_lesson", "", 1).strip()
        parts = [p.strip() for p in content.split("|")]
        if len(parts) < 3:
            await message.answer("❌ Қате пішім! Үлгі:\n`/add_lesson Өмірсеріков Бахтияр | ГЕО-01 | 28.10, 19:10`")
            return
        
        t_name, flow_name, lesson_time = parts[0], parts[1], parts[2]

        conn = sqlite3.connect("school_bot.db")
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM teachers WHERE full_name LIKE ?", (f"%{t_name}%",))
        teacher = cursor.fetchone()

        if not teacher:
            await message.answer(f"❌ '{t_name}' атты мұғалім базадан табылмады!")
            conn.close()
            return

        cursor.execute("INSERT INTO schedules (teacher_id, flow_name, subject, lesson_time) VALUES (?, ?, ?, ?)",
                       (teacher[0], flow_name, flow_name, lesson_time))
        conn.commit()
        conn.close()

        await message.answer(f"✅ Сабақ қосылды!\n👨‍🏫 Мұғалім: {t_name}\n📚 Поток: {flow_name}\n⏰ Уақыты: {lesson_time}")
    except Exception as e:
        await message.answer(f"❌ Қате орын алды: {e}")

@dp.message(Command("my_lessons"))
async def my_lessons(message: types.Message):
    conn = sqlite3.connect("school_bot.db")
    cursor = conn.cursor()
    
    # 1. Эдвайзер тексеру
    cursor.execute("SELECT full_name FROM advisors WHERE telegram_id = ?", (message.from_user.id,))
    advisor = cursor.fetchone()
    
    if advisor:
        a_name = advisor[0]
        cursor.execute("""
            SELECT s.flow_name, s.lesson_time, t.full_name 
            FROM schedules s 
            JOIN teachers t ON s.teacher_id = t.id 
            ORDER BY s.lesson_time
        """)
        lessons = cursor.fetchall()
        conn.close()

        if not lessons:
            await message.answer("Жүйеде ешқандай сабақтар тіркелмеген.")
            return

        text = f"🎓 **{a_name} (Академиялық эдвайзер) — Барлық ағымдардың кестесі:**\n\n"
        for f_name, l_time, t_name in lessons:
            text += f"• **{f_name}** — {l_time}\n  Мұғалім: {t_name}\n\n"
        await message.answer(text, parse_mode="Markdown")
        return

    # 2. Координатор тексеру
    cursor.execute("SELECT full_name, flow_name FROM coordinators WHERE telegram_id = ?", (message.from_user.id,))
    coord = cursor.fetchone()
    
    if coord:
        c_name, flow = coord
        cursor.execute("""
            SELECT s.flow_name, s.lesson_time, t.full_name 
            FROM schedules s 
            JOIN teachers t ON s.teacher_id = t.id 
            WHERE s.flow_name = ?
            ORDER BY s.lesson_time
        """, (flow,))
        lessons = cursor.fetchall()
        conn.close()

        if not lessons:
            await message.answer(f"'{flow}' потогы бойынша сабақтар табылмады.")
            return

        text = f"📋 **{c_name}, сіздің ағымыңыздың сабақ кестесі:**\n\n"
        for f_name, l_time, t_name in lessons:
            text += f"• {f_name} — {l_time}\n  Мұғалім: {t_name}\n\n"
        await message.answer(text, parse_mode="Markdown")
        return

    # 3. Мұғалім тексеру
    cursor.execute("SELECT id, full_name FROM teachers WHERE telegram_id = ?", (message.from_user.id,))
    teacher = cursor.fetchone()
    
    if teacher:
        cursor.execute("SELECT flow_name, lesson_time FROM schedules WHERE teacher_id = ? ORDER BY lesson_time", (teacher[0],))
        lessons = cursor.fetchall()
        conn.close()

        if not lessons:
            await message.answer("Сізде әлі сабақтар жоқ.")
            return

        text = f"📅 **{teacher[1]} — Сіздің сабақ кестеңіз:**\n\n"
        for f_name, l_time in lessons:
            text += f"• {f_name} — {l_time}\n"
        await message.answer(text, parse_mode="Markdown")
        return

    conn.close()
    await message.answer("Сіз жүйеге тіркелмегенсіз. `/start` арқылы өз атыңызды таңдаңыз.")

# Күн сайын 15:00-дегі автоматты хабарлама
async def daily_15_00_reminder():
    conn = sqlite3.connect("school_bot.db")
    cursor = conn.cursor()
    
    today_str = datetime.now().strftime("%d.%m")
    
    # 1. Координаторларға
    cursor.execute("SELECT telegram_id, flow_name FROM coordinators WHERE telegram_id IS NOT NULL")
    coordinators = cursor.fetchall()
    
    for t_id, flow in coordinators:
        cursor.execute("""
            SELECT s.flow_name, s.lesson_time, t.full_name 
            FROM schedules s 
            JOIN teachers t ON s.teacher_id = t.id 
            WHERE s.flow_name = ? AND s.lesson_time LIKE ?
        """, (flow, f"%{today_str}%"))
        lessons = cursor.fetchall()
        
        if lessons:
            schedule_text = ""
            for f_name, l_time, t_name in lessons:
                schedule_text += f"• {f_name} — {l_time}\n  Мұғалім: {t_name}\n"
            
            msg = (
                "Сәлеметсіз бе, координатор! Есіңізге ағымдағы қосымша сабақ уақытын саламын:\n\n"
                f"{schedule_text}"
            )
            try:
                await bot.send_message(t_id, msg)
            except Exception:
                pass

    # 2. Мұғалімдерге
    cursor.execute("SELECT telegram_id, id FROM teachers WHERE telegram_id IS NOT NULL")
    teachers = cursor.fetchall()
    
    for t_id, t_id_db in teachers:
        cursor.execute("SELECT flow_name, lesson_time FROM schedules WHERE teacher_id = ? AND lesson_time LIKE ?", (t_id_db, f"%{today_str}%"))
        lessons = cursor.fetchall()
        
        for flow_name, l_time in lessons:
            msg = (
                "Сәлеметсіз бе, мұғалім! Сізге алдағы қосымша сабақ уақытын еске саламыз:\n\n"
                f"• Уақыты: {l_time}\n"
                f"• Поток: {flow_name}"
            )
            try:
                await bot.send_message(t_id, msg)
            except Exception:
                pass

    # 3. Эдвайзерлерге (барлық бүгінгі сабақтар)
    cursor.execute("SELECT telegram_id, full_name FROM advisors WHERE telegram_id IS NOT NULL")
    advisors = cursor.fetchall()
    
    for a_id, a_name in advisors:
        cursor.execute("""
            SELECT s.flow_name, s.lesson_time, t.full_name 
            FROM schedules s 
            JOIN teachers t ON s.teacher_id = t.id 
            WHERE s.lesson_time LIKE ?
            ORDER BY s.lesson_time
        """, (f"%{today_str}%",))
        lessons = cursor.fetchall()
        
        if lessons:
            schedule_text = ""
            for f_name, l_time, t_name in lessons:
                schedule_text += f"• **{f_name}** — {l_time}\n  Мұғалім: {t_name}\n\n"
            
            msg = (
                f"Сәлеметсіз бе, эдвайзер {a_name}! Бүгінгі барлық қосымша сабақтар тізімі:\n\n"
                f"{schedule_text}"
            )
            try:
                await bot.send_message(a_id, msg, parse_mode="Markdown")
            except Exception:
                pass
                
    conn.close()

# 24 сағат бұрын еске салу
async def check_24h_reminders():
    conn = sqlite3.connect("school_bot.db")
    cursor = conn.cursor()
    
    now = datetime.now()
    
    cursor.execute("""
        SELECT s.id, s.flow_name, s.lesson_time, t.telegram_id, t.full_name, s.teacher_id 
        FROM schedules s 
        JOIN teachers t ON s.teacher_id = t.id
    """)
    schedules = cursor.fetchall()
    
    for s_id, flow_name, l_time_str, t_telegram_id, t_name, t_id_db in schedules:
        try:
            cleaned_time = l_time_str.replace("–", " ").split()[0]
            current_year = now.year
            if "." in cleaned_time and len(cleaned_time) <= 6:
                day, month = cleaned_time.split(".")
                time_part = l_time_str.split()[-1]
                hour, minute = time_part.split(":")
                lesson_dt = datetime(current_year, int(month), int(day), int(hour), int(minute))
                
                diff = abs((lesson_dt - now).total_seconds())
                if diff <= 60:
                    # 1. Мұғалімге
                    if t_telegram_id:
                        msg_teacher = (
                            "Сәлеметсіз бе, мұғалім! Сізге алдағы қосымша сабақ уақытын еске саламыз:\n\n"
                            f"• Уақыты: {l_time_str}\n"
                            f"• Поток: {flow_name}"
                        )
                        await bot.send_message(t_telegram_id, msg_teacher)
                        
                    # 2. Координаторға
                    cursor.execute("SELECT telegram_id FROM coordinators WHERE flow_name = ? AND telegram_id IS NOT NULL", (flow_name,))
                    coords = cursor.fetchall()
                    for (c_t_id,) in coords:
                        msg_coord = (
                            "Сәлеметсіз бе, координатор! Есіңізге ағымдағы қосымша сабақ уақытын саламын:\n\n"
                            f"📋 **{flow_name} ағымының кестесі:**\n"
                            f"• {flow_name} — {l_time_str}\n  Мұғалім: {t_name}"
                        )
                        await bot.send_message(c_t_id, msg_coord)

                    # 3. Барлық эдвайзерлерге
                    cursor.execute("SELECT telegram_id, full_name FROM advisors WHERE telegram_id IS NOT NULL")
                    advisors = cursor.fetchall()
                    for (a_t_id, a_name) in advisors:
                        msg_advisor = (
                            f"Сәлеметсіз бе, эдвайзер {a_name}! 24 сағаттан кейін басталатын сабақ:\n\n"
                            f"• Поток: {flow_name}\n"
                            f"• Уақыты: {l_time_str}\n"
                            f"• Мұғалім: {t_name}"
                        )
                        await bot.send_message(a_t_id, msg_advisor)
        except Exception:
            continue
            
    conn.close()

@dp.message(Command("test_broadcast"))
async def test_broadcast(message: types.Message):
    await daily_15_00_reminder()
    await message.answer("✅ Эдвайзерлерге және басқаларға тесттік еске салу хабарламалары жіберілді!")

async def main():
    scheduler.add_job(daily_15_00_reminder, 'cron', hour=15, minute=0)
    scheduler.add_job(check_24h_reminders, 'interval', minutes=1)
    
    scheduler.start()
    print("Эдвайзер рөлі қосылып, бот іске қосылды...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
