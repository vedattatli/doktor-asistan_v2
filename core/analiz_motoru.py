import os
import re
from typing import Dict, List, Optional, Tuple

import pdfplumber


class KlinikAnalizMotoru:
    """
    PDF raporundan laboratuvar satırlarını deterministik olarak ayrıştırır.
    LLM'e ham PDF yerine sadece doğrulanmış ve damgalanmış metin verir.
    """

    def __init__(self):
        # Genel numerik desenler
        self.sayi_re = re.compile(r"[-+]?\d+(?:[.,]\d+)?")
        self.aralik_re = re.compile(
            r"(?P<low>[-+]?\d+(?:[.,]\d+)?)\s*[-–]\s*(?P<high>[-+]?\d+(?:[.,]\d+)?)"
        )
        self.ust_sinir_re = re.compile(r"^(?:<=|≤|<)\s*(?P<high>\d+(?:[.,]\d+)?)$")
        self.alt_sinir_re = re.compile(r"^(?:>=|≥|>)\s*(?P<low>\d+(?:[.,]\d+)?)$")
        self.tarih_baslangic_re = re.compile(r"^\s*\d{2}\.\d{2}\.\d{4}\b")
        self.saat_baslangic_re = re.compile(r"^\s*(?:[01]\d|2[0-3]):[0-5]\d\b")

        # Test adı için kabul edilen karakter seti
        self.test_adi_re = re.compile(r"^[A-Za-zÇĞİÖŞÜçğıöşü][A-Za-z0-9ÇĞİÖŞÜçğıöşü#%()/.\- ]*$")
        self.satir_lab_re = re.compile(
            r"^\s*(?P<test>[A-Za-zÇĞİÖŞÜçğıöşü#%()/.\- ]+?)\s+(?P<kalan>.+)$"
        )

        self.atlanacak_satir_parcalari = [
            "t.c.sağlik bakanliği",
            "t.c.sağlık bakanlığı",
            "sağlık bilgi sistemleri genel müdürlüğü",
            "sonuç referans",
            "tarih tahlil sonuç",
            "birimi değeri",
            "enabiz.gov.tr",
            "sayfa ",
        ]

    def _temizle_metin(self, deger: Optional[str]) -> str:
        return re.sub(r"\s+", " ", (deger or "").replace("\n", " ")).strip()

    def _to_float(self, deger: Optional[str]) -> Optional[float]:
        if deger is None:
            return None
        try:
            return float(str(deger).replace(",", "."))
        except (TypeError, ValueError):
            return None

    def _sayiyi_yaz(self, sayi: Optional[float]) -> str:
        if sayi is None:
            return "?"
        if float(sayi).is_integer():
            return str(int(sayi))
        return f"{sayi:.15g}"

    def _test_adi_norm(self, ham_test: str) -> str:
        metin = self._temizle_metin(ham_test)
        metin = re.sub(r"\s+", " ", metin)
        # "WBC (BEYAZ KÜRE)" -> "WBC", "HGB(Hemoglobin)" -> "HGB"
        metin = metin.split("(")[0].strip()
        return metin

    def _referans_ayikla(self, ham_ref: str) -> Tuple[Optional[float], Optional[float]]:
        ref = self._temizle_metin(ham_ref)
        if not ref:
            return None, None

        aralik_eslesmeleri = list(self.aralik_re.finditer(ref))
        if aralik_eslesmeleri:
            son = aralik_eslesmeleri[-1]
            return self._to_float(son.group("low")), self._to_float(son.group("high"))

        ust = self.ust_sinir_re.match(ref)
        if ust:
            return None, self._to_float(ust.group("high"))

        alt = self.alt_sinir_re.match(ref)
        if alt:
            return self._to_float(alt.group("low")), None

        return None, None

    def _durum_hesapla(
        self, sonuc_degeri: Optional[float], ref_low: Optional[float], ref_high: Optional[float]
    ) -> str:
        # Damgalama sadece sonuç + referans varsa yapılır.
        if sonuc_degeri is None or (ref_low is None and ref_high is None):
            return "BİLİNMİYOR"

        if ref_low is not None and sonuc_degeri < ref_low:
            return "DÜŞÜK"
        if ref_high is not None and sonuc_degeri > ref_high:
            return "YÜKSEK"
        return "NORMAL"

    def _satir_atlanmali_mi(self, satir: str) -> bool:
        temiz = self._temizle_metin(satir)
        if not temiz:
            return True

        kucuk = temiz.lower()
        if any(parca in kucuk for parca in self.atlanacak_satir_parcalari):
            return True
        if self.tarih_baslangic_re.match(temiz):
            return True
        if self.saat_baslangic_re.match(temiz):
            return True
        if re.match(r"^\s*0\s*850", temiz):
            return True
        return False

    def _hasta_bilgisi_yakala(self, metin: str) -> Dict[str, str]:
        bilgiler = {
            "hasta_adi": "Bilinmiyor",
            "hastane": "Bilinmiyor",
            "tarih": "Bilinmiyor",
            "saat": "Bilinmiyor",
        }

        ad_eslesme = re.search(
            r"(?:Adı/Soyadı|Hasta Adı)\s*:\s*(.+?)(?:\s{2,}|Cinsiyet:|$)",
            metin,
            flags=re.IGNORECASE | re.MULTILINE,
        )
        if ad_eslesme:
            bilgiler["hasta_adi"] = self._temizle_metin(ad_eslesme.group(1))

        hastane_eslesme = re.search(
            r"(?:Sağlık Tesisi|Hastane)\s*:\s*(.+)",
            metin,
            flags=re.IGNORECASE,
        )
        if hastane_eslesme:
            bilgiler["hastane"] = self._temizle_metin(hastane_eslesme.group(1))

        tarih_eslesme = re.search(r"Tarih\s*:\s*(\d{2}\.\d{2}\.\d{4})", metin, flags=re.IGNORECASE)
        if tarih_eslesme:
            bilgiler["tarih"] = tarih_eslesme.group(1)
        else:
            herhangi_tarih = re.search(r"\b\d{2}\.\d{2}\.\d{4}\b", metin)
            if herhangi_tarih:
                bilgiler["tarih"] = herhangi_tarih.group(0)

        saat_eslesme = re.search(r"\b(?:[01]\d|2[0-3]):[0-5]\d\b", metin)
        if saat_eslesme:
            bilgiler["saat"] = saat_eslesme.group(0)

        return bilgiler

    def _satirdan_lab_kaydi(self, satir: str) -> Optional[Dict]:
        if self._satir_atlanmali_mi(satir):
            return None

        eslesme = self.satir_lab_re.match(satir)
        if not eslesme:
            return None

        ham_test = self._temizle_metin(eslesme.group("test"))
        if not ham_test or not self.test_adi_re.match(ham_test):
            return None

        kalan = self._temizle_metin(eslesme.group("kalan"))
        sonuc_eslesme = self.sayi_re.search(kalan)
        if not sonuc_eslesme:
            return None

        # KRİTİK: Sonuç, test adından SONRA gelen ilk sayıdır.
        sonuc_str = sonuc_eslesme.group(0)
        sonuc = self._to_float(sonuc_str)

        sonrasinda = kalan[sonuc_eslesme.end() :].strip()
        ref_match_list = list(self.aralik_re.finditer(sonrasinda))
        ref_low, ref_high = None, None
        unit = ""

        if ref_match_list:
            ref_match = ref_match_list[-1]
            unit = self._temizle_metin(sonrasinda[: ref_match.start()])
            ref_low, ref_high = self._referans_ayikla(ref_match.group(0))
        else:
            tokenlar = sonrasinda.split()
            if tokenlar:
                # "g/dL <=16" gibi vakalar
                pot_ref = self._temizle_metin(" ".join(tokenlar[-2:]))
                ref_low, ref_high = self._referans_ayikla(pot_ref)
                if ref_low is None and ref_high is None:
                    pot_ref = self._temizle_metin(tokenlar[-1])
                    ref_low, ref_high = self._referans_ayikla(pot_ref)
                if ref_low is not None or ref_high is not None:
                    ref_parca = pot_ref if self._referans_ayikla(pot_ref) != (None, None) else tokenlar[-1]
                    unit = self._temizle_metin(sonrasinda[: -len(ref_parca)])
                else:
                    unit = self._temizle_metin(sonrasinda)

        durum = self._durum_hesapla(sonuc, ref_low, ref_high)
        return {
            "test": self._test_adi_norm(ham_test),
            "value": sonuc if sonuc is not None else sonuc_str,
            "unit": unit or "",
            "ref_low": ref_low,
            "ref_high": ref_high,
            "status": durum,
        }

    def _tablodan_lab_kayitlari(self, sayfa) -> List[Dict]:
        tum_tablolar = []

        ilk_tablo = sayfa.extract_table()
        if ilk_tablo:
            tum_tablolar.append(ilk_tablo)

        diger_tablolar = sayfa.extract_tables() or []
        for tablo in diger_tablolar:
            if tablo not in tum_tablolar:
                tum_tablolar.append(tablo)

        kayitlar: List[Dict] = []

        for tablo in tum_tablolar:
            if not tablo:
                continue

            test_idx, value_idx, unit_idx, ref_idx = self._tablo_kolonlarini_bul(tablo)
            if test_idx is None or value_idx is None:
                continue

            for satir in tablo[1:]:
                hucreler = [self._temizle_metin(h) for h in (satir or [])]
                if not hucreler or not any(hucreler):
                    continue

                test_ham = hucreler[test_idx] if test_idx < len(hucreler) else ""
                if not test_ham:
                    continue

                test_norm = self._test_adi_norm(test_ham)
                if not test_norm or not self.test_adi_re.match(test_norm):
                    continue

                value_ham = hucreler[value_idx] if value_idx < len(hucreler) else ""
                sonuc = self._to_float(value_ham)
                if sonuc is None:
                    # Tabloda sonuç kolonu bozuksa satır parser fallback
                    satir_metin = " ".join([h for h in hucreler if h])
                    fallback = self._satirdan_lab_kaydi(satir_metin)
                    if fallback:
                        kayitlar.append(fallback)
                    continue

                unit = hucreler[unit_idx] if unit_idx is not None and unit_idx < len(hucreler) else ""
                ref_ham = hucreler[ref_idx] if ref_idx is not None and ref_idx < len(hucreler) else ""
                ref_low, ref_high = self._referans_ayikla(ref_ham)
                durum = self._durum_hesapla(sonuc, ref_low, ref_high)

                kayitlar.append(
                    {
                        "test": test_norm,
                        "value": sonuc,
                        "unit": unit or "",
                        "ref_low": ref_low,
                        "ref_high": ref_high,
                        "status": durum,
                    }
                )

        return kayitlar

    def _tablo_kolonlarini_bul(
        self, tablo: List[List[Optional[str]]]
    ) -> Tuple[Optional[int], Optional[int], Optional[int], Optional[int]]:
        vars_test = vars_value = vars_unit = vars_ref = None
        baslik = [self._temizle_metin(h).lower() for h in (tablo[0] or [])]

        for idx, ad in enumerate(baslik):
            if "tahlil" in ad or "test" in ad:
                vars_test = idx
            elif "sonuç" in ad and "birim" not in ad:
                vars_value = idx
            elif "birim" in ad:
                vars_unit = idx
            elif "referans" in ad:
                vars_ref = idx

        # Bilinen e-Nabız formatı fallback: [Tarih, Tahlil, Sonuç, Birim, Referans]
        if vars_test is None and len(baslik) >= 2:
            vars_test = 1
        if vars_value is None and len(baslik) >= 3:
            vars_value = 2
        if vars_unit is None and len(baslik) >= 4:
            vars_unit = 3
        if vars_ref is None and len(baslik) >= 5:
            vars_ref = 4

        return vars_test, vars_value, vars_unit, vars_ref

    def _sayfayi_render_et(self, patient: Dict[str, str], page_no: int, rows: List[Dict]) -> str:
        baslik = (
            f"--- HASTA: {patient['hasta_adi']} | TARİH: {patient['tarih']} | "
            f"SAAT: {patient['saat']} | KURUM: {patient['hastane']} | SAYFA: {page_no} ---"
        )
        satirlar = [baslik]

        emoji = {"NORMAL": "✅", "DÜŞÜK": "⬇️", "YÜKSEK": "⬆️", "BİLİNMİYOR": "❔"}
        for kayit in rows:
            unit_parca = f" {kayit['unit']}" if kayit["unit"] else ""
            ref_low = kayit.get("ref_low")
            ref_high = kayit.get("ref_high")
            if ref_low is not None and ref_high is not None:
                ref_yazi = f"{self._sayiyi_yaz(ref_low)}-{self._sayiyi_yaz(ref_high)}"
            elif ref_high is not None:
                ref_yazi = f"<={self._sayiyi_yaz(ref_high)}"
            elif ref_low is not None:
                ref_yazi = f">={self._sayiyi_yaz(ref_low)}"
            else:
                ref_yazi = "YOK"

            satirlar.append(
                "TEST: {test} | SONUÇ: {value}{unit} | REF: {ref} | DURUM: {status} {icon}".format(
                    test=kayit["test"],
                    value=self._sayiyi_yaz(self._to_float(str(kayit["value"]))),
                    unit=unit_parca,
                    ref=ref_yazi,
                    status=kayit["status"],
                    icon=emoji.get(kayit["status"], "❔"),
                )
            )

        return "\n".join(satirlar)

    def pdf_isle(self, dosya_yolu: str) -> List[Dict]:
        """
        Çıktı formatı (sayfa başına):
        {
          "page": int,
          "source": filename,
          "patient": {...},
          "rows": [...],
          "rendered_text": str
        }
        """
        cikti: List[Dict] = []
        kaynak = os.path.basename(dosya_yolu)

        try:
            with pdfplumber.open(dosya_yolu) as pdf:
                tum_metin = "\n".join([(sayfa.extract_text() or "") for sayfa in pdf.pages])
                patient = self._hasta_bilgisi_yakala(tum_metin)

                for sayfa in pdf.pages:
                    satirlar = []

                    # 1) Önce tablo dene (deterministik kolon bazlı)
                    tablo_kayitlari = self._tablodan_lab_kayitlari(sayfa)
                    if tablo_kayitlari:
                        satirlar = tablo_kayitlari
                    else:
                        # 2) Tablo yoksa metin satırı fallback
                        sayfa_metni = sayfa.extract_text() or ""
                        for ham_satir in sayfa_metni.splitlines():
                            kayit = self._satirdan_lab_kaydi(ham_satir)
                            if kayit:
                                satirlar.append(kayit)

                    rendered = self._sayfayi_render_et(patient, sayfa.page_number, satirlar)
                    cikti.append(
                        {
                            "page": sayfa.page_number,
                            "source": kaynak,
                            "patient": patient,
                            "rows": satirlar,
                            "rendered_text": rendered,
                        }
                    )
        except Exception as hata:
            print(f"PDF işleme hatası ({kaynak}): {hata}")
            return []

        return cikti
