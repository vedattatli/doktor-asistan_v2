# --- LINUX SQLITE FIX (ChromaDB için kritik) ---
try:
    __import__('pysqlite3')
    import sys
    sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')
except ImportError:
    pass

import streamlit as st
import chromadb
import os
import shutil
from core.analiz_motoru import KlinikAnalizMotoru
from core.ingestion import ingest_pdf
from core.retrieval import query_db
from core.generation import generate_answer
from core.alanlar.lab.df_uret import parsed_pages_to_df
from core.grafik import GrafikRenderHatasi, render
from core.grafik.planner_llm import GrafikPlanlamaHatasi, plan_chart_spec
from core.grafik_modulu import list_parsed_jsons, load_parsed_json

# --- 1. SİSTEM AYARLARI VE DİZİNLER ---
st.set_page_config(page_title="Profesyonel Klinik Asistan v3.5", layout="wide")

DB_PATH = "./data/db"
PDF_DIR = "./data/pdfs"
COLLECTION_NAME = "klinik_v3"
os.makedirs(DB_PATH, exist_ok=True)
os.makedirs(PDF_DIR, exist_ok=True)
SAFE_DELETE_ROOTS = [os.path.abspath("./data"), os.path.abspath("./uploads")]

# Analiz motorunu (beyni) başlatıyoruz
motor = KlinikAnalizMotoru()

# Grafik isteği için basit router anahtar kelimeleri.
GRAFIK_ANAHTAR_KELIMELER = (
    "grafik",
    "chart",
    "trend",
    "çiz",
    "ciz",
    "plot",
    "heatmap",
    "korelasyon",
)

# --- 2. VERİTABANI VE HAFIZA İŞLEMLERİ ---

def sisteme_kaydet(dosya_yolu, koleksiyon, analiz_motoru):
    """
    Analiz motorunu kullanarak PDF'i işler ve
    doğrulanmış verileri ChromaDB hafızasına kaydeder.
    """
    return ingest_pdf(dosya_yolu, koleksiyon, motor=analiz_motoru)

def veritabanini_sifirla():
    """
    Koleksiyonu güvenli biçimde silip yeniden oluşturur.
    """
    try:
        st.session_state.db_client.delete_collection(name=COLLECTION_NAME)
    except Exception:
        # Koleksiyon yoksa/boşsa sessizce devam.
        pass
    st.session_state.koleksiyon = st.session_state.db_client.get_or_create_collection(name=COLLECTION_NAME)


def grafik_istegi_mi(soru: str) -> bool:
    metin = (soru or "").lower()
    return any(anahtar in metin for anahtar in GRAFIK_ANAHTAR_KELIMELER)


def df_schema_ozeti_uret(df):
    kolonlar = ", ".join([f"{k}:{str(v)}" for k, v in df.dtypes.to_dict().items()])
    testler = sorted([t for t in df["test"].dropna().astype(str).unique().tolist() if t]) if "test" in df.columns else []
    return (
        f"satir_sayisi={len(df)}\n"
        f"kolonlar={kolonlar}\n"
        f"ornek_testler={testler[:20]}"
    )


def rapor_izinli_testleri_uret(parsed_pages):
    df = parsed_pages_to_df(parsed_pages)
    if df.empty or "test" not in df.columns:
        return []
    return sorted([t for t in df["test"].dropna().astype(str).unique().tolist() if t])


def spec_kullanilan_testleri(spec):
    testler = set()
    data = spec.data
    for tek in [data.test, data.x_test, data.y_test]:
        if tek:
            testler.add(str(tek))
    testler.update([str(t) for t in (data.tests or []) if t])
    testler.update([str(t) for t in (data.series or []) if t])
    return sorted(testler)


def grafik_menu_mesaji(available_tests, rapor_secili=True):
    if not rapor_secili:
        return "Grafik için önce bir rapor seç."
    if not available_tests:
        return "Bu raporda çizilebilir test bulamadım."

    secenekler = ", ".join(available_tests[:6])
    if len(available_tests) > 6:
        secenekler = f"{secenekler} …"
    varsayilan = ", ".join(available_tests[:2])
    return (
        f"Seçenekler: {secenekler}\n"
        "Hangisini çizeyim?\n"
        f"Varsayılan: {varsayilan} trendi"
    )


def grafik_sorusu_belirsiz_mi(soru: str, available_tests: list[str]) -> bool:
    metin = (soru or "").lower()
    if any(anahtar in metin for anahtar in ("trend", "korelasyon", "scatter", "heatmap", "ısı", "isi")):
        return False
    if any(str(test).lower() in metin for test in available_tests):
        return False
    return any(anahtar in metin for anahtar in ("grafik", "chart", "plot", "çiz", "ciz"))


def _guvenli_yol_mu(path: str) -> bool:
    abs_path = os.path.abspath(path)
    for kok in SAFE_DELETE_ROOTS:
        if abs_path == kok or abs_path.startswith(kok + os.sep):
            return True
    return False


def _guvenli_sil(path: str) -> bool:
    if not path:
        return False
    abs_path = os.path.abspath(path)
    if not _guvenli_yol_mu(abs_path):
        return False
    try:
        if os.path.isfile(abs_path):
            os.remove(abs_path)
            return True
        if os.path.isdir(abs_path):
            shutil.rmtree(abs_path)
            return True
    except Exception:
        return False
    return False


def secili_hastayi_sil(secili_json: str, collection):
    if not secili_json:
        return False, "Silinecek bir rapor seçili değil."
    if secili_json != os.path.basename(secili_json):
        return False, "Geçersiz dosya seçimi."

    pdf_adi = secili_json[:-5] if secili_json.endswith(".json") else secili_json
    parsed_yol = os.path.join("data", "parsed", secili_json)
    pdf_yol = os.path.join(PDF_DIR, pdf_adi)
    index_klasor = os.path.join(DB_PATH, pdf_adi)

    silindi = any(
        [
            _guvenli_sil(parsed_yol),
            _guvenli_sil(pdf_yol),
            _guvenli_sil(index_klasor),
        ]
    )

    try:
        collection.delete(where={"source": pdf_adi})
        silindi = True
    except Exception:
        pass

    if not silindi:
        return False, "Seçili hasta için silinecek veri bulunamadı."
    return True, "Seçili hasta verileri silindi."

# --- 3. KULLANICI ARAYÜZÜ (STREAMLIT) ---

# Veritabanı bağlantısını oturum bazlı başlatıyoruz
if "db_client" not in st.session_state:
    st.session_state.db_client = chromadb.PersistentClient(path=DB_PATH)
if "koleksiyon" not in st.session_state:
    st.session_state.koleksiyon = st.session_state.db_client.get_or_create_collection(name=COLLECTION_NAME)

# Yan Panel: Dosya Yükleme ve Yönetim
with st.sidebar:
    st.title("📂 Klinik Arşiv Yönetimi")
    st.info("Lütfen hastaya ait hemogram veya laboratuvar PDF'lerini yükleyin.")
    
    yuklenenler = st.file_uploader("Hasta Raporu Seç (PDF)", type="pdf", accept_multiple_files=True)
    
    if yuklenenler and st.button("Analiz Motorunu Çalıştır"):
        with st.spinner("Motor verileri doğruluyor ve indeksliyor..."):
            for dosya in yuklenenler:
                yol = os.path.join(PDF_DIR, dosya.name)
                with open(yol, "wb") as f:
                    f.write(dosya.getbuffer())

                # Motoru çalıştırıp veritabanına sayfa chunk olarak kaydediyoruz
                adet = sisteme_kaydet(yol, st.session_state.koleksiyon, motor)
                kayitlar = st.session_state.koleksiyon.get(
                    where={"source": dosya.name},
                    include=["metadatas"],
                )
                metalar = kayitlar.get("metadatas") or []
                aktif_hasta = next(
                    (
                        m.get("patient_name")
                        for m in metalar
                        if isinstance(m, dict) and (m.get("patient_name") or "").strip()
                    ),
                    None,
                )
                if aktif_hasta and aktif_hasta != "Bilinmiyor":
                    st.session_state["active_patient_name"] = aktif_hasta
                json_adi = f"{dosya.name}.json"
                try:
                    parsed_rapor = load_parsed_json(json_adi)
                    st.session_state["allowed_tests_for_active_report"] = rapor_izinli_testleri_uret(parsed_rapor)
                    st.session_state["selected_parsed_report"] = json_adi
                except Exception:
                    st.session_state["allowed_tests_for_active_report"] = []
                st.toast(f"{dosya.name}: {adet} sayfa işlendi ve doğrulandı.")
            st.success("Tüm raporlar klinik hafızaya alındı. Sorgulamaya başlayabilirsiniz.")

    st.markdown("---")
    if st.button("🧹 Sohbet Geçmişini Temizle"):
        st.session_state.messages = []
        st.rerun()
    if st.button("🗑️ Veritabanını Sıfırla"):
        veritabanini_sifirla()
        st.success("Koleksiyon sıfırlandı ve yeniden oluşturuldu.")
        st.rerun()

with st.sidebar:
    st.markdown("---")
    st.subheader("📊 Grafik Modu")
    json_files = list_parsed_jsons()
    if json_files:
        secili = st.session_state.get("selected_parsed_report")
        if secili not in json_files:
            secili = json_files[0]
        st.session_state.selected_parsed_report = st.selectbox(
            "Rapor seç (parsed JSON)",
            options=json_files,
            index=json_files.index(secili),
        )
        try:
            parsed_rapor = load_parsed_json(st.session_state["selected_parsed_report"])
            st.session_state["allowed_tests_for_active_report"] = rapor_izinli_testleri_uret(parsed_rapor)
        except Exception:
            st.session_state["allowed_tests_for_active_report"] = []
        st.caption("Grafik sorularında seçilen rapor kullanılacak.")
        if st.button("🧯 Hastayı Sil (PDF+JSON+Index)"):
            basarili, mesaj = secili_hastayi_sil(
                st.session_state.get("selected_parsed_report"),
                st.session_state.koleksiyon,
            )
            if basarili:
                st.session_state["selected_parsed_report"] = None
                st.session_state["allowed_tests_for_active_report"] = []
                st.session_state["active_patient_name"] = None
                st.success(mesaj)
                st.rerun()
            else:
                st.warning(mesaj)
    else:
        st.session_state["selected_parsed_report"] = None
        st.session_state["allowed_tests_for_active_report"] = []
        st.info("Henüz parse edilmiş rapor yok. Önce PDF yükleyip analiz et.")
        
# Ana Ekran Başlığı
st.title("🩺 Profesyonel Klinik Asistan")
st.caption("Analiz Motoru Destekli Tıbbi Veri Doğrulama Sistemi")

# Sohbet Geçmişini Görüntüle
if "messages" not in st.session_state:
    st.session_state.messages = []

for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

# Kullanıcı Girişi (Sorgu Ekranı)
if sorgu := st.chat_input("Örn: Enes Aktürk'ün HGB durumu nedir?"):
    # Kullanıcı mesajını ekrana yaz ve geçmişe kaydet
    st.session_state.messages.append({"role": "user", "content": sorgu})
    with st.chat_message("user"):
        st.markdown(sorgu)

    if grafik_istegi_mi(sorgu):
        with st.chat_message("assistant"):
            available_tests = []
            secili_rapor = st.session_state.get("selected_parsed_report")
            if not secili_rapor:
                menu = grafik_menu_mesaji([], rapor_secili=False)
                st.info(menu)
                st.session_state.messages.append({"role": "assistant", "content": menu})
                st.stop()
            try:
                parsed_pages = load_parsed_json(secili_rapor)
                df = parsed_pages_to_df(parsed_pages)
                if df.empty:
                    raise GrafikPlanlamaHatasi("Seçili raporda çizilebilir veri bulunamadı.")

                available_tests = sorted(
                    [t for t in df["test"].dropna().astype(str).unique().tolist() if t]
                )
                if grafik_sorusu_belirsiz_mi(sorgu, available_tests):
                    menu = grafik_menu_mesaji(available_tests, rapor_secili=True)
                    st.info(menu)
                    st.session_state.messages.append({"role": "assistant", "content": menu})
                    st.stop()
                else:
                    allowed_tests = st.session_state.get("allowed_tests_for_active_report") or []
                    planner_tests = allowed_tests if allowed_tests else available_tests
                    spec = plan_chart_spec(
                        user_text=sorgu,
                        df_schema_summary=df_schema_ozeti_uret(df),
                        available_tests=planner_tests,
                    )
                    if allowed_tests:
                        kullanilan_testler = spec_kullanilan_testleri(spec)
                        izinli_kume = set(allowed_tests)
                        gecersiz = [t for t in kullanilan_testler if t not in izinli_kume]
                        if gecersiz:
                            izinli_yazi = ", ".join(allowed_tests)
                            raise GrafikPlanlamaHatasi(
                                f"Bu raporda yalnızca şu testler kullanılabilir: {izinli_yazi}"
                            )
                    fig = render(spec, df)
                    st.plotly_chart(fig, use_container_width=True)

                    bilgi = f"Grafik üretildi: {spec.template.value}"
                    st.caption(bilgi)
                    st.session_state.messages.append({"role": "assistant", "content": bilgi})

            except GrafikPlanlamaHatasi:
                menu = grafik_menu_mesaji(available_tests, rapor_secili=bool(secili_rapor))
                st.info(menu)
                st.session_state.messages.append({"role": "assistant", "content": menu})
            except GrafikRenderHatasi:
                hata = "Grafik oluşturulamadı. Lütfen test adını daha net yaz."
                st.error(hata)
                st.session_state.messages.append({"role": "assistant", "content": hata})
            except Exception:
                hata = "Grafik isteği işlenemedi. Lütfen tekrar dene."
                st.error(hata)
                st.session_state.messages.append({"role": "assistant", "content": hata})
    else:
        # 1) Retrieval: sayfa bilgili doğrulanmış parçaları getir
        aktif_hasta = st.session_state.get("active_patient_name")
        meta_filtre = {"patient_name": aktif_hasta} if aktif_hasta else None
        context_docs, context_metas = query_db(
            st.session_state.koleksiyon, sorgu, n_results=6, filter_meta=meta_filtre
        )

        # 2) Generation: sadece context'ten konuş
        with st.chat_message("assistant"):
            cevap_kutusu = st.empty()
            tam_cevap = ""

            try:
                cevap = generate_answer(sorgu, context_docs, context_metas)

                if isinstance(cevap, str):
                    tam_cevap = cevap
                    cevap_kutusu.markdown(tam_cevap)
                else:
                    for parca in cevap:
                        tam_cevap += parca["message"]["content"]
                        cevap_kutusu.markdown(tam_cevap + "▌")

                cevap_kutusu.markdown(tam_cevap)
                st.session_state.messages.append({"role": "assistant", "content": tam_cevap})

            except Exception:
                hata = "Yanıt üretilirken geçici bir sorun oluştu. Lütfen tekrar dene."
                st.error(hata)
                st.session_state.messages.append({"role": "assistant", "content": hata})
