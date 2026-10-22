"""
Backend Flask untuk visualisasi Bubble Sort & Insertion Sort.

POST /api/sort   Body: {"numbers": [5, 3, 8, 4, 6, 2]}
Response:
  bubble_steps / insertion_steps -> array of arrays (frame per swap / per insert)
  bubble_trace / insertion_trace -> daftar event detail untuk animasi. Tiap event:
      op       : start | compare | swap | key | shift | place | pass_end | break | done
      lines    : nomor baris kode (di panel kode frontend) yang sedang dijalankan
      arr      : isi array pada langkah itu (dipakai frontend untuk cek 1:1)
      swap     : [a, b] posisi dua kotak yang bertukar (hanya di event swap/shift)
      pair/gt  : pasangan yang dibandingkan & hasil perbandingannya
      sorted   : posisi yang sudah final (hijau), boundary: posisi garis pemisah
"""

from pathlib import Path
from flask import Flask, jsonify, request, send_from_directory

BASE_DIR = Path(__file__).resolve().parent.parent
PUBLIC_DIR = BASE_DIR / "public"
app = Flask(__name__, static_folder=str(PUBLIC_DIR), static_url_path="")

MAX_ITEMS = 6    # maksimal 6 angka
MAX_VALUE = 99   # tiap angka 0-99 (satuan maupun puluhan)


def ev(op, lines, view, **extra):
    """Buat satu event + snapshot array saat itu."""
    return {"op": op, "lines": lines, "arr": list(view), **extra}


def bubble_trace(numbers):
    arr, n = list(numbers), len(numbers)
    t = [ev("start", [2], arr, sorted=[], boundary=n)]
    for i in range(n - 1):
        limit, swapped = n - 1 - i, False
        base = dict(i=i, limit=limit, boundary=n - i, sorted=list(range(n - i, n)))
        for j in range(limit):
            gt = arr[j] > arr[j + 1]                    # strict '>' -> stabil
            t.append(ev("compare", [6], arr, j=j, pair=[j, j + 1], gt=gt, **base))
            if gt:
                arr[j], arr[j + 1] = arr[j + 1], arr[j]
                swapped = True
                t.append(ev("swap", [7, 8], arr, j=j, swap=[j, j + 1], **base))
        t.append(ev("pass_end", [9], arr, i=i, limit=limit,
                    boundary=n - 1 - i, sorted=list(range(n - 1 - i, n))))
        if not swapped:                                 # tanpa swap = sudah urut
            t.append(ev("break", [10], arr, i=i, limit=limit,
                        boundary=None, sorted=list(range(n))))
            break
    t.append(ev("done", [11], arr, boundary=None, sorted=list(range(n))))
    return t


def insertion_trace(numbers):
    """
    `arr` mengikuti kode asli (geser ke kanan lalu sisipkan key).
    `view` adalah tampilan visual: key "berjalan" ke kiri dengan menukar
    tetangganya, hasil akhirnya sama persis dengan arr.
    """
    arr, n = list(numbers), len(numbers)
    view = arr.copy()
    t = [ev("start", [1], view, boundary=1, sorted=[0])]
    for i in range(1, n):
        key, j, kp = arr[i], i - 1, i                   # kp = posisi key di view

        def mk(op, lines, **kw):
            return ev(op, lines, view, i=i, key=key, keypos=kp, boundary=i + 1, **kw)

        def sorted_now():
            return [p for p in range(i + 1) if p != kp]

        t.append(mk("key", [3, 4], j=j, sorted=sorted_now()))
        while True:
            gt = j >= 0 and arr[j] > key
            t.append(mk("compare", [5], j=j, pair=[j, kp] if j >= 0 else None,
                        gt=gt, sorted=sorted_now()))
            if not gt:
                break
            arr[j + 1] = arr[j]                         # geser elemen besar
            view[j], view[j + 1] = view[j + 1], view[j]
            kp, j = j, j - 1
            t.append(mk("shift", [6, 7], j=j, swap=[kp, kp + 1], sorted=sorted_now()))
        arr[j + 1] = key                                # sisipkan key
        t.append(mk("place", [8], j=j, sorted=list(range(i + 1))))
    t.append(ev("done", [9], view, boundary=None, sorted=list(range(n))))
    return t


def to_steps(trace, kind):
    """Turunkan 'array of arrays' (frame per swap / per insert) dari trace."""
    frames = [trace[0]["arr"]]
    for e in trace:
        if kind == "bubble" and e["op"] == "swap":
            frames.append(e["arr"])
        if kind == "insertion" and e["op"] == "place" and e["keypos"] != e["i"]:
            frames.append(e["arr"])
    return frames


def validate_numbers(payload):
    if not isinstance(payload, dict) or "numbers" not in payload:
        return None, "Body JSON harus berisi key 'numbers'."
    numbers = payload["numbers"]
    if not isinstance(numbers, list):
        return None, "'numbers' harus berupa list."
    if len(numbers) < 2:
        return None, "Masukkan minimal 2 angka."
    if len(numbers) > MAX_ITEMS:
        return None, f"Maksimal {MAX_ITEMS} angka."
    for v in numbers:
        if isinstance(v, bool) or not isinstance(v, int):
            return None, "Semua elemen 'numbers' harus berupa bilangan bulat."
        if not 0 <= v <= MAX_VALUE:
            return None, f"Setiap angka harus antara 0 dan {MAX_VALUE}."
    if len(set(numbers)) != len(numbers):
        return None, "Angka tidak boleh ada yang sama."
    return numbers, None


@app.route("/api/sort", methods=["POST"])
def sort_endpoint():
    numbers, error = validate_numbers(request.get_json(silent=True))
    if error:
        return jsonify({"error": error}), 400
    bt, it = bubble_trace(numbers), insertion_trace(numbers)
    return jsonify({
        "bubble_steps": to_steps(bt, "bubble"),
        "insertion_steps": to_steps(it, "insertion"),
        "bubble_trace": bt,
        "insertion_trace": it,
    })


@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


@app.route("/", methods=["GET"])
def index():
    if (PUBLIC_DIR / "index.html").exists():
        return send_from_directory(str(PUBLIC_DIR), "index.html")
    return jsonify({"status": "API running"})


# Tes lokal: python api/index.py -> buka http://127.0.0.1:5000
if __name__ == "__main__":
    app.run(debug=True, port=5000)