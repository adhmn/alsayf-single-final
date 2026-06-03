
import re
from pathlib import Path
from datetime import datetime
import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk

SIGNATURE = 'SR8/sFMDSR8IDi8Q4kICCMPvfNHAUzb3vs+6ymr6rInIr5AE6ULKQKVTCWUYIncc7J49L5K85FZsbVT2D6BCK+pfD2Kf6yihUMY9hO6NuGx3QR/8kvW0cdF1rRCc+95s0yNWIE9Y0kwJXWZu9tRm+wh6DivGLfCE7kNDEf/fKkH0GkH2DSliGLImIEWm4YI1fFKEr9nJtahZH8c9bgxS7bJ6LTobGTyQOM55GQKG9mFyP1vgKg2gSwV5uBk47/P5kU09J2UyORXyp/ijFUj3BFFhwYdMBE0ob0Ghb4YMSYQuQbrfLgqx38Xi1FasyTkOyLnx2nDt4X67kCfKZHhd8A=='

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

BANK_CODE = "RJHI"
EMPLOYER_ID = "00068776"
EMPLOYER_ACCOUNT = "SA3180000584608016210209"
CURRENCY = "SAR"
DEFAULT_UNIFIED = "1-2753169210"
DEFAULT_EST_NO = "09-2106130"
DEFAULT_CENTRAL_REF = "1090807233"

def clean_amount(v):
    v = str(v or "").replace(",", "").replace("ريال", "").replace("ر.س", "").strip()
    m = re.search(r"\d+(?:\.\d+)?", v)
    return float(m.group(0)) if m else 0.0

def amount(v):
    return f"{int(round(float(v or 0))):013d},00"

def find_iban(line):
    s = line.upper().replace(" ", "").replace("-", "")
    m = re.search(r"(SA[A-Z0-9]{22})", s)
    return m.group(1) if m else ""

def parse_workers(text, default_salary):
    lines = [x.strip() for x in text.splitlines() if x.strip()]
    company = ""
    unified = ""
    workers = []
    cur = {}

    for line in lines:
        if line.startswith("مؤسسة") or line.startswith("شركة"):
            company = line
            continue

        if "رقم موحد" in line or re.fullmatch(r"\d{1,3}\s*-\s*\d{5,12}", line):
            m = re.search(r"(\d{1,3})\s*-\s*(\d{5,12})", line)
            if m:
                unified = f"{m.group(1)}-{m.group(2)}"
            continue

        if re.match(r"^(الاسم|اسم)\s*[:：]", line):
            if cur.get("name"):
                workers.append(cur)
                cur = {}
            cur["name"] = re.sub(r"^(الاسم|اسم)\s*[:：]\s*", "", line).strip()
            continue

        if "رقم الهوية" in line or "الهوية" in line or "الإقامة" in line or "الاقامة" in line:
            ids = re.findall(r"\d{7,15}", line)
            if ids:
                cur["id"] = ids[0]
            continue

        ib = find_iban(line)
        if ib:
            cur["iban"] = ib
            continue

        if re.fullmatch(r"[\d,]+(?:\.\d+)?(?:\s*ريال)?", line):
            cur["salary"] = clean_amount(line)
            continue

    if cur.get("name"):
        workers.append(cur)

    final = []
    for w in workers:
        final.append({
            "name": w.get("name", "").strip(),
            "id": w.get("id", "").strip(),
            "iban": w.get("iban", "").strip(),
            "salary": float(w.get("salary", default_salary) or default_salary or 0),
        })
    return company, unified, final

def validate(unified, workers):
    errors = []
    if not unified:
        errors.append("الرقم الموحد مفقود")
    if not workers:
        errors.append("لم يتم استخراج أي عامل")
    for i, w in enumerate(workers, 1):
        if not w["name"]:
            errors.append(f"العامل {i}: الاسم مفقود")
        if not w["id"]:
            errors.append(f"العامل {i}: رقم الهوية مفقود")
        if not w["iban"]:
            errors.append(f"العامل {i}: الآيبان مفقود")
        elif not re.fullmatch(r"SA[A-Z0-9]{22}", w["iban"]):
            errors.append(f"العامل {i}: الآيبان غير صحيح")
        if w["salary"] <= 0:
            errors.append(f"العامل {i}: الراتب مفقود أو صفر")
    return errors

def build_txt(unified, est_no, central_start, workers):
    today = datetime.now().strftime("%Y%m%d")
    total = sum(w["salary"] for w in workers)

    lines = []
    lines.append("\t".join([
        BANK_CODE,
        f"{EMPLOYER_ID:<11}",
        EMPLOYER_ACCOUNT,
        CURRENCY,
        today,
        amount(total),
        today,
        f"{unified:<18}",
        f"{'P000':<7}",
        f"{est_no:<18}",
    ]))

    try:
        base_ref = int(central_start)
    except Exception:
        base_ref = int(DEFAULT_CENTRAL_REF)

    for i, w in enumerate(workers, 1):
        gross = amount(w["salary"])
        central = f"Centralization Ref:{base_ref + i - 1}"
        ref = datetime.now().strftime("%y%m%d") + f"{i:010d}"
        lines.append("\t".join([
            gross,
            f"{w['iban']:<36}",
            f"{w['name']:<140}",
            f"RJHI".ljust(140),
            central.ljust(140),
            "      ",
            gross,
            "0000000000000,00",
            "0000000000000,00",
            "0000000000000,00",
            w["id"],
            ref,
            "Success ",
            today,
        ]))

    lines.append("-")
    lines.append(SIGNATURE)
    return "\n".join(lines)

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("السيف")
        self.geometry("470x700")
        self.minsize(455, 660)
        self.configure(fg_color="#171717")

        ctk.CTkLabel(self, text="السيف", font=("Arial", 30, "bold"), text_color="#00c8ff").pack(pady=(10, 0))
        ctk.CTkLabel(self, text="أداة تجهيز ملف الأجور", font=("Arial", 12), text_color="#eeeeee").pack(pady=(0, 8))

        self.e_unified = ctk.CTkEntry(self, width=420, height=34, justify="center", placeholder_text="الرقم الموحد")
        self.e_unified.insert(0, DEFAULT_UNIFIED)
        self.e_unified.pack(pady=3)

        row1 = ctk.CTkFrame(self, fg_color="transparent")
        row1.pack(pady=3)
        self.e_non = ctk.CTkEntry(row1, width=205, height=34, justify="center", placeholder_text="راتب غير السعودي")
        self.e_non.insert(0, "2000")
        self.e_non.pack(side="left", padx=5)
        self.e_sa = ctk.CTkEntry(row1, width=205, height=34, justify="center", placeholder_text="راتب السعودي")
        self.e_sa.insert(0, "5000")
        self.e_sa.pack(side="right", padx=5)

        self.e_ref = ctk.CTkEntry(self, width=420, height=34, justify="center", placeholder_text="Centralization Ref")
        self.e_ref.insert(0, DEFAULT_CENTRAL_REF)
        self.e_ref.pack(pady=3)

        self.e_est = ctk.CTkEntry(self, width=420, height=34, justify="center", placeholder_text="رقم المنشأة / رقم ملف البنك")
        self.e_est.insert(0, DEFAULT_EST_NO)
        self.e_est.pack(pady=3)

        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill="x", padx=20, pady=(5, 5))
        top.grid_columnconfigure((0, 1, 2, 3), weight=1)
        ctk.CTkButton(top, text="لصق", height=32, command=self.paste).grid(row=0, column=0, padx=3, sticky="ew")
        ctk.CTkButton(top, text="تحديد الكل", height=32, fg_color="#555", command=self.select_all).grid(row=0, column=1, padx=3, sticky="ew")
        ctk.CTkButton(top, text="فحص", height=32, fg_color="#777", command=self.check).grid(row=0, column=2, padx=3, sticky="ew")
        ctk.CTkButton(top, text="توليد", height=32, fg_color="#18c8e8", command=self.generate).grid(row=0, column=3, padx=3, sticky="ew")

        frame = ctk.CTkFrame(self, fg_color="#202020", border_width=1, border_color="#666")
        frame.pack(fill="both", expand=True, padx=20, pady=(2, 6))
        self.text = tk.Text(frame, bg="#202020", fg="white", insertbackground="white", font=("Arial", 12), relief="flat", wrap="word", padx=10, pady=10)
        self.text.pack(fill="both", expand=True, padx=8, pady=8)
        self.text.bind("<Control-v>", self.paste_event)
        self.text.bind("<Control-a>", self.select_all_event)
        self.text.bind("<Button-3>", self.menu_popup)

        self.menu = tk.Menu(self, tearoff=0)
        self.menu.add_command(label="تحديد الكل", command=self.select_all)
        self.menu.add_command(label="لصق", command=self.paste)
        self.menu.add_command(label="نسخ", command=lambda: self.text.event_generate("<<Copy>>"))

        bottom = ctk.CTkFrame(self, fg_color="transparent")
        bottom.pack(fill="x", padx=20, pady=(0, 8))
        bottom.grid_columnconfigure((0, 1), weight=1)
        ctk.CTkButton(bottom, text="حذف", height=38, fg_color="#b0182f", command=lambda: self.text.delete("1.0", "end")).grid(row=0, column=0, padx=4, sticky="ew")
        ctk.CTkButton(bottom, text="توليد ملف", height=38, fg_color="#18c8e8", font=("Arial", 13, "bold"), command=self.generate).grid(row=0, column=1, padx=4, sticky="ew")

        self.status = ctk.CTkLabel(self, text="جاهز", text_color="#ffd84d", font=("Arial", 11, "bold"))
        self.status.pack(pady=(0, 5))

    def select_all_event(self, event=None):
        self.select_all()
        return "break"

    def select_all(self):
        self.text.tag_add("sel", "1.0", "end")
        self.text.focus_set()

    def paste_event(self, event=None):
        self.paste()
        return "break"

    def paste(self):
        try:
            self.text.insert("insert", self.clipboard_get())
        except Exception:
            messagebox.showwarning("تنبيه", "لا يوجد نص منسوخ")

    def menu_popup(self, event):
        self.menu.tk_popup(event.x_root, event.y_root)

    def get_data(self):
        default_salary = clean_amount(self.e_non.get())
        company, unified_from_text, workers = parse_workers(self.text.get("1.0", "end"), default_salary)
        unified = self.e_unified.get().strip() or unified_from_text
        if unified_from_text and not self.e_unified.get().strip():
            self.e_unified.insert(0, unified_from_text)
        return unified, workers

    def check(self):
        unified, workers = self.get_data()
        errors = validate(unified, workers)
        if errors:
            messagebox.showerror("نواقص", "\n".join(errors[:40]))
        else:
            messagebox.showinfo("الفحص", f"الفحص سليم\nعدد العمال: {len(workers)}")

    def generate(self):
        unified, workers = self.get_data()
        errors = validate(unified, workers)
        if errors:
            messagebox.showerror("لا يمكن توليد ملف ناقص", "\n".join(errors[:40]))
            return

        path = filedialog.asksaveasfilename(
            title="اختار مكان حفظ ملف الأجور",
            defaultextension=".txt",
            initialfile=f"WPS_File_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
            filetypes=[("Text Files", "*.txt")]
        )
        if not path:
            return

        content = build_txt(unified, self.e_est.get().strip(), self.e_ref.get().strip(), workers)
        Path(path).write_text(content, encoding="utf-8")
        self.status.configure(text="تم توليد الملف")
        messagebox.showinfo("تم", f"تم توليد الملف بنجاح:\n{path}")

if __name__ == "__main__":
    App().mainloop()
