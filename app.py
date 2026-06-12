import streamlit as st
from googleapiclient.discovery import build
import pandas as pd
import re

# ==========================================
# إعدادات الواجهة والتهيئة
# ==========================================
st.set_page_config(page_title="أستوديو يوتيوب الذكي", page_icon="📊", layout="wide")

# ⚠️ ضع مفتاح YouTube Data API v3 الخاص بك هنا لكي يعمل التطبيق بشكل صحيح
YOUTUBE_API_KEY = "AIzaSyDIVRliNx8SPt3n5hBuosxumpXdOpwddYQ"

# دالة لبناء اتصال مع API اليوتيوب
def get_youtube_client():
    if YOUTUBE_API_KEY == "اكتب_مفتاحك_هنا" or not YOUTUBE_API_KEY:
        st.error("رجاءً قم بإدخال مفتاح الـ API السرّي الخاص بك في المتغير YOUTUBE_API_KEY داخل الكود.")
        return None
    return build("youtube", "v3", developerKey=YOUTUBE_API_KEY)

# دالة استخراج الـ Channel ID من الرابط أو المعرف
def extract_channel_id(input_string):
    input_string = input_string.strip()
    if input_string.startswith("UC") and len(input_string) == 24:
        return input_string
    
    # محاولة استخراج المعرف إذا تم إدخال رابط مخصص أو اسم مستخدم (@)
    youtube = get_youtube_client()
    if not youtube:
        return None
        
    handle = None
    if "@" in input_string:
        handle = input_string.split("@")[-1].split("/")[0]
    elif "youtube.com/c/" in input_string:
        handle = input_string.split("youtube.com/c/")[-1].split("/")[0]
    elif "youtube.com/user/" in input_string:
        handle = input_string.split("youtube.com/user/")[-1].split("/")[0]
        
    if handle:
        try:
            res = youtube.search().list(q=f"@{handle}", type="channel", part="id", maxResults=1).execute()
            if res.get("items"):
                return res["items"][0]["id"]["channelId"]
        except Exception:
            pass
            
    # إذا لم ينجح، نحاول البحث كـ نص عادي عن القناة
    try:
        res = youtube.search().list(q=input_string, type="channel", part="id", maxResults=1).execute()
        if res.get("items"):
            return res["items"][0]["id"]["channelId"]
    except Exception as e:
        st.error(f"حدث خطأ أثناء تحديد معرف القناة: {e}")
    return None

# ==========================================
# واجهة المستخدم (Streamlit UI)
# ==========================================
st.markdown("<h1 style='text-align: center; color: #FF0000;'>📊 أستوديو يوتيوب المصغر الذكي</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #888;'>أداة متكاملة لتحليل القنوات، ومراقبة الفيديوهات، واكتشاف الأفكار الرابحة.</p>", unsafe_allow_html=True)
st.write("---")

# تفعيل التبويبات الثلاثة المطلوبة
tab1, tab2, tab3 = st.tabs(["📈 تحليل القناة", "🎥 أداء آخر الفيديوهات", "💡 كاشف الأفكار والتريند"])

youtube = get_youtube_client()

if youtube:
    # ------------------------------------------
    # القسم الأول: تحليل القنوات
    # ------------------------------------------
    with tab1:
        st.header("🔍 فحص وتحليل القناة")
        channel_input = st.text_input("أدخل رابط القناة، أو اسم المستخدم (مثال: @TariSoor)، أو الـ Channel ID مباشرة:", "")
        
        if channel_input:
            channel_id = extract_channel_id(channel_input)
            if channel_id:
                try:
                    response = youtube.channels().list(part="snippet,statistics", id=channel_id).execute()
                    if response.get("items"):
                        channel_data = response["items"][0]
                        snippet = channel_data["snippet"]
                        stats = channel_data["statistics"]
                        
                        # تخزين الـ channel_id في جلسة العمل للاستفادة منها في القسم الثاني
                        st.session_state["active_channel_id"] = channel_id
                        st.session_state["uploads_playlist_id"] = channel_data.get("contentDetails", {}).get("relatedPlaylists", {}).get("uploads")
                        
                        # عرض البطاقات الإحصائية
                        st.markdown(f"### 📌 قمت بفحص: **{snippet['title']}**")
                        
                        col1, col2, col3, col4 = st.columns(4)
                        col1.metric(label="👥 المشتركون", value=f"{int(stats.get('subscriberCount', 0)):,}")
                        col2.metric(label="👁️ إجمالي المشاهدات", value=f"{int(stats.get('viewCount', 0)):,}")
                        col3.metric(label="🎬 عدد الفيديوهات", value=f"{int(stats.get('videoCount', 0)):,}")
                        col4.metric(label="🆔 معرف القناة المعتمد", value=channel_id)
                        
                        st.image(snippet["thumbnails"]["medium"]["url"], width=150, caption="شعار القناة الحالي")
                    else:
                        st.warning("لم يتم العثور على بيانات لهذه القناة. تأكد من صحة الرابط.")
                except Exception as e:
                    st.error(f"خطأ أثناء جلب إحصائيات القناة: {e}")
            else:
                st.error("تعذر استخراج معرف القناة (Channel ID)، يرجى التحقق من المدخلات.")

    # ------------------------------------------
    # القسم الثاني: تحليل الفيديوهات
    # ------------------------------------------
    with tab2:
        st.header("📊 أداء آخر 10 فيديوهات")
        # التحقق من وجود قناة تم فحصها مسبقاً في التبويب الأول
        active_id = st.session_state.get("active_channel_id")
        
        if not active_id:
            st.info("💡 برجاء فحص قناة أولاً في التبويب الأول ليتم عرض آخر فيديوهاتها هنا تلقائياً.")
        else:
            try:
                # جلب آخر الفيديوهات المرفوعة عبر البحث بالـ channelId وترتيبها بالتاريخ
                search_res = youtube.search().list(
                    channelId=active_id,
                    part="id,snippet",
                    order="date",
                    type="video",
                    maxResults=10
                ).execute()
                
                video_ids = [item["id"]["videoId"] for item in search_res.get("items", [])]
                
                if video_ids:
                    # جلب تفاصيل المشاهدات والتفاعل لكل فيديو بدقة
                    video_res = youtube.videos().list(
                        part="snippet,statistics",
                        id=",".join(video_ids)
                    ).execute()
                    
                    video_list = []
                    for vid in video_res.get("items", []):
                        v_stats = vid["statistics"]
                        v_snippet = vid["snippet"]
                        
                        video_list.append({
                            "عنوان الفيديو": v_snippet["title"],
                            "تاريخ النشر": v_snippet["publishedAt"][:10],
                            "👁️ المشاهدات": int(v_stats.get("viewCount", 0)),
                            "👍 الإعجابات": int(v_stats.get("likeCount", 0)),
                            "💬 التعليقات": int(v_stats.get("commentCount", 0)),
                            "رابط الفيديو": f"https://youtube.com/watch?v={vid['id']}"
                        })
                    
                    df = pd.DataFrame(video_list)
                    # عرض الجدول التفاعلي الأنيق لبيانات الفيديوهات
                    st.dataframe(
                        df, 
                        column_config={
                            "رابط الفيديو": st.column_config.LinkColumn("رابط التشغيل")
                        },
                        use_container_width=True
                    )
                else:
                    st.warning("لم يتم العثور على فيديوهات عامة منشورة في هذه القناة.")
            except Exception as e:
                st.error(f"حدث خطأ أثناء جلب الفيديوهات: {e}")

    # ------------------------------------------
    # القسم الثالث: البحث عن الأفكار والتريند
    # ------------------------------------------
    with tab3:
        st.header("💡 كاشف الأفكار واستلهام التريند")
        st.write("اكتب الكلمة المفتاحية أو النيش الذي تود البحث عنه، وسيجلب لك التطبيق أعلى 5 فيديوهات مشاهدة للتعلم منها ومعرفة أسرار نجاحها.")
        
        search_query = st.text_input("كلمة البحث (مثال: قصص تاريخية غامضة، سيكولوجية الجماهير):", "")
        
        if search_query:
            try:
                # البحث عن الفيديوهات وترتيبها بالأعلى مشاهدة (viewCount)
                search_response = youtube.search().list(
                    q=search_query,
                    part="id,snippet",
                    type="video",
                    order="viewCount",
                    maxResults=5
                ).execute()
                
                trend_ids = [item["id"]["videoId"] for item in search_response.get("items", [])]
                
                if trend_ids:
                    trend_res = youtube.videos().list(
                        part="snippet,statistics",
                        id=",".join(trend_ids)
                    ).execute()
                    
                    st.markdown(f"### 🔥 أعلى 5 فيديوهات تصدراً في مجال: **{search_query}**")
                    
                    for idx, vid in enumerate(trend_res.get("items", [])):
                        t_snippet = vid["snippet"]
                        t_stats = vid["statistics"]
                        v_url = f"https://youtube.com/watch?v={vid['id']}"
                        
                        # تنسيق العرض على شكل بطاقات أفقية أنيقة
                        with st.container():
                            col_thumb, col_desc = st.columns([1, 3])
                            with col_thumb:
                                st.image(t_snippet["thumbnails"]["medium"]["url"], use_container_width=True)
                            with col_desc:
                                st.subheader(f"{idx+1}. {t_snippet['title']}")
                                st.markdown(f"**القناة:** {t_snippet['channelTitle']} | **تاريخ النشر:** {t_snippet['publishedAt'][:10]}")
                                st.markdown(f"👁️ **المشاهدات:** {int(t_stats.get('viewCount', 0)):,} | 👍 **الإعجابات:** {int(t_stats.get('likeCount', 0)):,}")
                                st.markdown(f"[🔗 اضغط هنا لمشاهدة الفيديو وتحليله]({v_url})")
                            st.write("---")
                else:
                    st.info("لم يتم العثور على نتائج بحث تطابق هذه الكلمة المفتاحية.")
            except Exception as e:
                st.error(f"حدث خطأ أثناء إجراء البحث: {e}")

# ==========================================
# دليل التثبيت والتشغيل (يُعرض في الـ Terminal كتعليق للمطور)
# ==========================================
# [طريقة التثبيت والتشغيل]:
# 1. افتح الـ Terminal أو موجه الأوامر في مجلد المشروع.
# 2. قم بتثبيت المكتبات المطلوبة عبر الأمر التالي:
#    pip install streamlit google-api-python-client pandas
# 3. لحفظ وتشغيل الكود، اكتب في الـ Terminal:
#    streamlit run app.py
# 4. سيفتح لك التطبيق تلقائياً في المتصفح على الاستضافة المحلية (Localhost).
