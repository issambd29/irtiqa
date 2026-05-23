import json
import math
import random
from datetime import date, timedelta
from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST, require_http_methods
from django.http import JsonResponse
from django.contrib.auth.models import User
from .forms import StyledUserCreationForm
from .models import UserProfile, DailyProgress, CustomTask, CustomSection, CustomHabit, HabitLog

QUOTES = [
    {'ar': 'إن مع العسر يسرا', 'en': 'Verily, with hardship comes ease'},
    {'ar': 'من جد وجد', 'en': 'Whoever strives shall find'},
    {'ar': 'العلم نور', 'en': 'Knowledge is light'},
    {'ar': 'الصبر مفتاح الفرج', 'en': 'Patience is the key to relief'},
    {'ar': 'خير الناس أنفعهم للناس', 'en': 'The best people are those most beneficial to others'},
    {'ar': 'اطلبوا العلم من المهد إلى اللحد', 'en': 'Seek knowledge from the cradle to the grave'},
    {'ar': 'حاسبوا أنفسكم قبل أن تحاسبوا', 'en': 'Hold yourselves accountable before you are held accountable'},
]


def get_or_create_today(user):
    today = date.today()
    progress, _ = DailyProgress.objects.get_or_create(user=user, date=today)
    return progress


def update_streak_and_xp(user, progress):
    profile = user.profile
    today = date.today()

    yesterday = today - timedelta(days=1)
    if profile.last_completed_date == yesterday:
        profile.streak_days += 1
    elif profile.last_completed_date != today:
        if progress.completion_pct(profile) >= 80:
            profile.streak_days = 1

    if progress.completion_pct(profile) >= 80:
        profile.last_completed_date = today

    all_days = DailyProgress.objects.filter(user=user)
    total_xp = sum(d.calculate_xp(profile) for d in all_days)
    profile.total_xp = total_xp
    profile.save()


def circ_offset(pct, r=54.5):
    circ = 2 * math.pi * r
    return round(circ - (pct / 100) * circ, 2)


# ── Auth ──────────────────────────────────────────────────────────────────────

def landing(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    return render(request, 'landing.html')


def register(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    if request.method == 'POST':
        form = StyledUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            UserProfile.objects.get_or_create(user=user)
            login(request, user)
            return redirect('dashboard')
    else:
        form = StyledUserCreationForm()
    return render(request, 'registration/register.html', {'form': form})


# ── Pages ─────────────────────────────────────────────────────────────────────

@login_required
def dashboard(request):
    progress = get_or_create_today(request.user)
    profile = request.user.profile
    tasks = CustomTask.objects.filter(user=request.user, date=date.today())
    completion = progress.completion_pct(profile)
    prayers_done = sum([progress.fajr, progress.dhuhr, progress.asr, progress.maghrib, progress.isha])

    tasks_done = sum(1 for t in tasks if t.done)
    tasks_total = tasks.count()
    tasks_pct = int((tasks_done / tasks_total) * 100) if tasks_total else 0

    # Domain completion percentages
    physical_goals = [progress.workout_done, progress.sleep_hours >= profile.sleep_target, progress.water_glasses >= profile.water_target]
    physical_pct = int((sum(physical_goals) / len(physical_goals)) * 100)

    knowledge_goals = [progress.reading_minutes >= profile.reading_target, progress.english_minutes >= 20, progress.books_pages > 0]
    knowledge_pct = int((sum(knowledge_goals) / len(knowledge_goals)) * 100)

    islamic_goals = [prayers_done == 5, progress.morning_adhkar, progress.evening_adhkar, progress.quran_pages >= profile.quran_daily_target, progress.qiyam]
    islamic_pct = int((sum(islamic_goals) / len(islamic_goals)) * 100)

    programming_goals = [progress.coding_minutes >= profile.coding_target, progress.pomodoros_done >= 4]
    programming_pct = int((sum(programming_goals) / len(programming_goals)) * 100)

    # Weekly chart data (last 7 days)
    today = date.today()
    week_labels = []
    week_data = []
    day_names_ar = ['الأحد', 'الاثنين', 'الثلاثاء', 'الأربعاء', 'الخميس', 'الجمعة', 'السبت']
    day_names_en = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']
    for i in range(6, -1, -1):
        d = today - timedelta(days=i)
        lang = profile.language
        week_labels.append(day_names_en[d.weekday()] if lang == 'en' else day_names_ar[d.weekday()])
        try:
            dp = DailyProgress.objects.get(user=request.user, date=d)
            week_data.append(dp.completion_pct(profile))
        except DailyProgress.DoesNotExist:
            week_data.append(0)

    ctx = {
        'progress': progress,
        'profile': profile,
        'tasks': tasks,
        'tasks_done': tasks_done,
        'tasks_pct': tasks_pct,
        'completion': completion,
        'circ_offset': circ_offset(completion),
        'prayers_done': prayers_done,
        'physical_pct': physical_pct,
        'knowledge_pct': knowledge_pct,
        'islamic_pct': islamic_pct,
        'programming_pct': programming_pct,
        'quote': random.choice(QUOTES),
        'streak_range': range(1, 8),
        'week_labels': json.dumps(week_labels),
        'week_data': json.dumps(week_data),
        'page': 'dashboard',
    }
    return render(request, 'tracker/dashboard.html', ctx)


@login_required
def islamic(request):
    progress = get_or_create_today(request.user)
    profile = request.user.profile
    prayers_done = sum([progress.fajr, progress.dhuhr, progress.asr, progress.maghrib, progress.isha])
    quran_pct = min(100, int((progress.quran_pages / max(profile.quran_daily_target, 1)) * 100))
    ctx = {
        'progress': progress,
        'profile': profile,
        'prayers_done': prayers_done,
        'quran_pct': quran_pct,
        'page': 'islamic',
    }
    return render(request, 'tracker/islamic.html', ctx)


@login_required
def physical(request):
    progress = get_or_create_today(request.user)
    profile = request.user.profile
    water_pct = min(100, int((progress.water_glasses / max(profile.water_target, 1)) * 100))
    workout_types = ['Gym', 'Running', 'Swimming', 'Cycling', 'Yoga', 'Football', 'Basketball', 'Home workout']
    ctx = {
        'progress': progress,
        'profile': profile,
        'water_pct': water_pct,
        'water_range': range(1, profile.water_target + 1),
        'workout_types': workout_types,
        'page': 'physical',
    }
    return render(request, 'tracker/physical.html', ctx)


@login_required
def knowledge(request):
    progress = get_or_create_today(request.user)
    profile = request.user.profile
    reading_pct = min(100, int((progress.reading_minutes / max(profile.reading_target, 1)) * 100))
    english_pct = min(100, int((progress.english_minutes / 20) * 100))
    english_activities = [
        {'icon': '📖', 'label_ar': 'قراءة', 'label': 'Reading', 'mins': 15},
        {'icon': '🎧', 'label_ar': 'استماع', 'label': 'Listening', 'mins': 20},
        {'icon': '✍️', 'label_ar': 'كتابة', 'label': 'Writing', 'mins': 15},
        {'icon': '🗣️', 'label_ar': 'محادثة', 'label': 'Speaking', 'mins': 30},
    ]
    ctx = {
        'progress': progress,
        'profile': profile,
        'reading_pct': reading_pct,
        'english_pct': english_pct,
        'english_activities': english_activities,
        'page': 'knowledge',
    }
    return render(request, 'tracker/knowledge.html', ctx)


@login_required
def programming(request):
    progress = get_or_create_today(request.user)
    profile = request.user.profile
    coding_pct = min(100, int((progress.coding_minutes / max(profile.coding_target, 1)) * 100))
    ctx = {
        'progress': progress,
        'profile': profile,
        'coding_pct': coding_pct,
        'page': 'programming',
    }
    return render(request, 'tracker/programming.html', ctx)


@login_required
def stats(request):
    profile = request.user.profile
    ctx = {
        'profile': profile,
        'page': 'stats',
    }
    return render(request, 'tracker/stats.html', ctx)


@login_required
def achievements(request):
    profile = request.user.profile
    all_progress = DailyProgress.objects.filter(user=request.user)

    total_prayers = sum(sum([d.fajr, d.dhuhr, d.asr, d.maghrib, d.isha]) for d in all_progress)
    total_quran = sum(d.quran_pages for d in all_progress)
    total_workouts = sum(1 for d in all_progress if d.workout_done)
    total_coding_days = sum(1 for d in all_progress if d.coding_minutes >= profile.coding_target)
    total_reading_days = sum(1 for d in all_progress if d.reading_minutes >= profile.reading_target)

    def ach(title_ar, title_en, desc_ar, desc_en, icon, unlocked):
        return {
            'title_ar': title_ar, 'title_en': title_en,
            'desc_ar': desc_ar, 'desc_en': desc_en,
            'icon': icon, 'unlocked': unlocked,
        }

    achievement_list = [
        ach('المبتدئ', 'First Step', 'سجّل أول صلاة', 'Log your first prayer', '🕌', total_prayers >= 1),
        ach('المواظب', 'Dedicated', 'صلّ 5 صلوات في يوم واحد', 'Pray all 5 in one day', '⭐', any(
            sum([d.fajr, d.dhuhr, d.asr, d.maghrib, d.isha]) == 5 for d in all_progress
        )),
        ach('حافظ القرآن', 'Quran Reader', 'اقرأ 50 صفحة من القرآن', 'Read 50 Quran pages total', '📖', total_quran >= 50),
        ach('المجتهد', 'Striver', 'سلسلة 7 أيام', '7-day streak', '🔥', profile.streak_days >= 7),
        ach('المثابر', 'Consistent', 'سلسلة 30 يومًا', '30-day streak', '🌟', profile.streak_days >= 30),
        ach('المحارب', 'Warrior', 'أكمل 10 تمارين', 'Complete 10 workouts', '💪', total_workouts >= 10),
        ach('المبرمج', 'Coder', 'برمج 10 أيام', 'Code for 10 days', '⌨', total_coding_days >= 10),
        ach('القارئ', 'Reader', 'اقرأ 20 يومًا', 'Read for 20 days', '📚', total_reading_days >= 20),
        ach('الخبير', 'Expert', 'اجمع 1000 نقطة XP', 'Earn 1000 XP total', '🏆', profile.total_xp >= 1000),
        ach('الأسطورة', 'Legend', 'اجمع 5000 نقطة XP', 'Earn 5000 XP total', '👑', profile.total_xp >= 5000),
        ach('عابد', 'Devout', 'صلّ 100 صلاة', 'Pray 100 total prayers', '🕋', total_prayers >= 100),
        ach('العالم', 'Scholar', 'اقرأ 100 صفحة قرآن', 'Read 100 Quran pages', '🌙', total_quran >= 100),
    ]

    # Level map data
    LEVELS = [
        (1, 'مبتدئ', 'Beginner', 0),
        (2, 'مركّز', 'Focused', 500),
        (3, 'منضبط', 'Disciplined', 1500),
        (4, 'مخلص', 'Dedicated', 3000),
        (5, 'طالب علم', 'Seeker', 6000),
        (6, 'متقن', 'Master', 10000),
    ]
    current_level = profile.get_level()
    level_map = []
    for num, name_ar, name_en, xp_req in LEVELS:
        level_map.append({
            'number': num,
            'name_ar': name_ar,
            'name_en': name_en,
            'xp_required': xp_req,
            'current': num == current_level,
            'reached': profile.total_xp >= xp_req,
        })

    # XP table
    xp_table = [
        {'name_ar': 'الصلوات الخمس', 'name_en': 'Five Prayers', 'xp': 80},
        {'name_ar': 'صلاة في المسجد', 'name_en': 'Mosque Prayer', 'xp': 50},
        {'name_ar': 'قراءة القرآن (كل ساعة)', 'name_en': 'Quran Reading (per hour)', 'xp': 100},
        {'name_ar': 'الجلوس بعد الفجر', 'name_en': 'Sitting after Fajr', 'xp': 40},
        {'name_ar': 'قيام الليل', 'name_en': 'Night Prayer', 'xp': 60},
        {'name_ar': 'أذكار الصباح', 'name_en': 'Morning Adhkar', 'xp': 20},
        {'name_ar': 'أذكار المساء', 'name_en': 'Evening Adhkar', 'xp': 20},
        {'name_ar': 'البرمجة ساعة', 'name_en': 'Coding (1 hour)', 'xp': 70},
        {'name_ar': 'قراءة 10 صفحات', 'name_en': 'Reading 10 pages', 'xp': 30},
        {'name_ar': 'تمرين رياضي', 'name_en': 'Workout', 'xp': 40},
        {'name_ar': 'أكل صحي', 'name_en': 'Healthy Eating', 'xp': 25},
        {'name_ar': 'النوم الساعة 11', 'name_en': 'Sleep by 11pm', 'xp': 30},
    ]

    ctx = {
        'profile': profile,
        'achievements': achievement_list,
        'unlocked_count': sum(1 for a in achievement_list if a['unlocked']),
        'total_count': len(achievement_list),
        'level_map': level_map,
        'xp_table': xp_table,
        'page': 'achievements',
    }
    return render(request, 'tracker/achievements.html', ctx)


@login_required
def settings_view(request):
    profile = request.user.profile
    ctx = {
        'profile': profile,
        'page': 'settings',
    }
    return render(request, 'tracker/settings.html', ctx)


# ── API ───────────────────────────────────────────────────────────────────────

@login_required
@require_http_methods(["POST"])
def api_update(request):
    try:
        data = json.loads(request.body)
        field = data.get('field')
        value = data.get('value')
        today = date.today()

        progress, _ = DailyProgress.objects.get_or_create(user=request.user, date=today)
        profile = request.user.profile

        bool_fields = [
            'fajr', 'dhuhr', 'asr', 'maghrib', 'isha',
            'morning_adhkar', 'evening_adhkar', 'workout_done', 'qiyam',
            'matn_memorization', 'learned_something',
        ]
        int_fields = [
            'quran_pages', 'water_glasses', 'books_pages', 'pomodoros_done',
            'reading_minutes', 'english_minutes', 'coding_minutes',
            'istighfar_count', 'salawat_count', 'english_words',
        ]
        float_fields = ['sleep_hours']
        str_fields = ['workout_type', 'book_name', 'reading_notes', 'learning_notes']

        if field in bool_fields:
            setattr(progress, field, bool(value))
        elif field in int_fields:
            setattr(progress, field, int(value))
        elif field in float_fields:
            setattr(progress, field, float(value))
        elif field in str_fields:
            setattr(progress, field, str(value))
        else:
            return JsonResponse({'error': 'Unknown field'}, status=400)

        progress.save()
        update_streak_and_xp(request.user, progress)
        profile.refresh_from_db()

        return JsonResponse({
            'ok': True,
            'xp_today': progress.calculate_xp(profile),
            'total_xp': profile.total_xp,
            'level': profile.get_level(),
            'level_pct': profile.get_level_progress_pct(),
            'streak': profile.streak_days,
            'completion': progress.completion_pct(profile),
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required
@require_http_methods(["POST"])
def api_custom_tasks(request):
    try:
        data = json.loads(request.body)
        action = data.get('action')
        today = date.today()

        if action == 'add':
            label = data.get('label', '').strip()
            if not label:
                return JsonResponse({'error': 'Empty label'}, status=400)
            task = CustomTask.objects.create(user=request.user, date=today, label=label)
            return JsonResponse({'ok': True, 'id': task.id, 'label': task.label, 'done': task.done})

        elif action == 'toggle':
            task_id = data.get('id')
            task = CustomTask.objects.get(id=task_id, user=request.user)
            task.done = not task.done
            task.save()
            return JsonResponse({'ok': True, 'done': task.done})

        elif action == 'delete':
            task_id = data.get('id')
            CustomTask.objects.filter(id=task_id, user=request.user).delete()
            return JsonResponse({'ok': True})

        return JsonResponse({'error': 'Unknown action'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required
def api_stats_data(request):
    profile = request.user.profile
    days_back = int(request.GET.get('days', 30))
    today = date.today()
    start = today - timedelta(days=days_back - 1)

    progress_qs = DailyProgress.objects.filter(
        user=request.user, date__gte=start
    ).order_by('date')
    progress_map = {p.date: p for p in progress_qs}

    labels, xp_data, prayers_data, quran_data, sleep_data, coding_data = [], [], [], [], [], []

    for i in range(days_back):
        d = start + timedelta(days=i)
        labels.append(d.strftime('%m/%d'))
        p = progress_map.get(d)
        if p:
            xp_data.append(p.calculate_xp(profile))
            prayers_data.append(sum([p.fajr, p.dhuhr, p.asr, p.maghrib, p.isha]))
            quran_data.append(p.quran_pages)
            sleep_data.append(p.sleep_hours)
            coding_data.append(p.coding_minutes)
        else:
            xp_data.append(0); prayers_data.append(0); quran_data.append(0)
            sleep_data.append(0); coding_data.append(0)

    return JsonResponse({
        'labels': labels, 'xp': xp_data, 'prayers': prayers_data,
        'quran': quran_data, 'sleep': sleep_data, 'coding': coding_data,
        'total_xp': profile.total_xp, 'streak': profile.streak_days,
        'level': profile.get_level(),
    })


@login_required
def my_system(request):
    today = date.today()
    sections = CustomSection.objects.filter(user=request.user, is_active=True).prefetch_related('habits')
    section_data = []
    for section in sections:
        habits_data = []
        for habit in section.habits.filter(is_active=True):
            try:
                log = HabitLog.objects.get(habit=habit, user=request.user, date=today)
                value = log.value
            except HabitLog.DoesNotExist:
                value = 0.0
            if habit.habit_type == 'boolean':
                done = value >= 1
                pct = 100 if done else 0
            else:
                done = value >= habit.target
                pct = min(100, int((value / max(habit.target, 1)) * 100))
            habits_data.append({'habit': habit, 'value': value, 'done': done, 'pct': pct})
        done_count = sum(1 for h in habits_data if h['done'])
        total_count = len(habits_data)
        section_pct = int((done_count / total_count) * 100) if total_count else 0
        section_data.append({
            'section': section,
            'habits': habits_data,
            'done': done_count,
            'total': total_count,
            'pct': section_pct,
        })
    ctx = {
        'section_data': section_data,
        'profile': request.user.profile,
        'page': 'my_system',
    }
    return render(request, 'tracker/my_system.html', ctx)


# ── Personal Life OS API ───────────────────────────────────────────────────────

@login_required
@require_http_methods(["POST"])
def api_sections(request):
    try:
        data = json.loads(request.body)
        action = data.get('action')
        if action == 'create':
            name = data.get('name', '').strip()
            icon = data.get('icon', '⭐').strip() or '⭐'
            if not name:
                return JsonResponse({'error': 'Name required'}, status=400)
            order = CustomSection.objects.filter(user=request.user).count()
            section = CustomSection.objects.create(user=request.user, name=name, icon=icon, order=order)
            return JsonResponse({'ok': True, 'id': section.id, 'name': section.name, 'icon': section.icon})
        elif action == 'update':
            section = CustomSection.objects.get(id=data.get('id'), user=request.user)
            if 'name' in data and data['name'].strip():
                section.name = data['name'].strip()
            if 'icon' in data and data['icon'].strip():
                section.icon = data['icon'].strip()
            section.save()
            return JsonResponse({'ok': True})
        elif action == 'delete':
            CustomSection.objects.filter(id=data.get('id'), user=request.user).delete()
            return JsonResponse({'ok': True})
        return JsonResponse({'error': 'Unknown action'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required
@require_http_methods(["POST"])
def api_habits(request):
    try:
        data = json.loads(request.body)
        action = data.get('action')
        if action == 'create':
            section = CustomSection.objects.get(id=data.get('section_id'), user=request.user)
            name = data.get('name', '').strip()
            if not name:
                return JsonResponse({'error': 'Name required'}, status=400)
            habit = CustomHabit.objects.create(
                section=section, user=request.user,
                name=name,
                icon=data.get('icon', '✓').strip() or '✓',
                habit_type=data.get('habit_type', 'boolean'),
                target=float(data.get('target', 1)),
                unit=data.get('unit', '').strip(),
                xp_reward=int(data.get('xp_reward', 10)),
                order=section.habits.count(),
            )
            return JsonResponse({
                'ok': True, 'id': habit.id, 'name': habit.name, 'icon': habit.icon,
                'habit_type': habit.habit_type, 'target': habit.target,
                'unit': habit.unit, 'xp_reward': habit.xp_reward,
            })
        elif action == 'delete':
            CustomHabit.objects.filter(id=data.get('id'), user=request.user).delete()
            return JsonResponse({'ok': True})
        return JsonResponse({'error': 'Unknown action'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required
@require_http_methods(["POST"])
def api_habit_log(request):
    try:
        data = json.loads(request.body)
        habit = CustomHabit.objects.get(id=data.get('habit_id'), user=request.user)
        today = date.today()
        log, _ = HabitLog.objects.get_or_create(habit=habit, user=request.user, date=today)
        old_value = log.value
        log.value = float(data.get('value', 0))
        log.save()
        done = log.value >= habit.target if habit.habit_type != 'boolean' else log.value >= 1
        old_done = old_value >= habit.target if habit.habit_type != 'boolean' else old_value >= 1
        xp_earned = 0
        profile = request.user.profile
        if done and not old_done:
            xp_earned = habit.xp_reward
            profile.total_xp += xp_earned
            profile.save()
        elif not done and old_done:
            profile.total_xp = max(0, profile.total_xp - habit.xp_reward)
            profile.save()
        profile.refresh_from_db()
        return JsonResponse({
            'ok': True, 'done': done, 'value': log.value, 'xp_earned': xp_earned,
            'total_xp': profile.total_xp, 'level': profile.get_level(),
            'level_pct': profile.get_level_progress_pct(),
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required
@require_http_methods(["POST"])
def api_settings(request):
    try:
        data = json.loads(request.body)
        profile = request.user.profile
        if 'language' in data:
            profile.language = data['language']
        if 'quran_daily_target' in data:
            profile.quran_daily_target = int(data['quran_daily_target'])
        if 'sleep_target' in data:
            profile.sleep_target = float(data['sleep_target'])
        if 'water_target' in data:
            profile.water_target = int(data['water_target'])
        if 'reading_target' in data:
            profile.reading_target = int(data['reading_target'])
        if 'coding_target' in data:
            profile.coding_target = int(data['coding_target'])
        profile.save()
        return JsonResponse({'ok': True})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)
