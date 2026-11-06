"""Editorial starting points, not a live trend feed or performance forecast."""
TOPICS = {
    "general": (),
    "habits": ("habit", "focus", "routine", "productivity", "consistent", "discipline"),
    "tech": ("technology", "tool", "software", "ai", "automation", "workflow"),
    "career": ("career", "interview", "job", "work", "skill", "learn"),
    "culture": ("indonesia", "culture", "food", "tradition", "travel", "language"),
}
IDEAS = [
    dict(topic="habits", name="Kebiasaan & produktivitas", duration=30, hook="The small habit that made the biggest difference",
         angle="Ambil satu kebiasaan konkret: masalah, perubahan kecil, lalu pengalaman hasilnya.",
         reason="Bisa dipahami tanpa harus mengenal tokoh atau konteks lokal.",
         search="small habits productivity podcast practical routine",
         check="Pilih pengalaman yang benar-benar diceritakan pembicara; hindari janji hasil universal."),
    dict(topic="tech", name="Teknologi yang praktis", duration=45, hook="One task, two workflows: what actually changed?",
         angle="Cari demonstrasi satu alat atau perbandingan proses kerja sebelum dan sesudah.",
         reason="Contoh yang terlihat membantu penonton mengikuti penjelasan lintas bahasa.",
         search="practical technology workflow tutorial demonstration",
         check="Pastikan alat/versi masih relevan; jangan mengarang klaim penghematan waktu."),
    dict(topic="career", name="Cerita karier & pelajaran", duration=45, hook="The career mistake I wish I had understood earlier",
         angle="Pilih cerita yang punya keputusan, konsekuensi, dan satu pelajaran yang jelas.",
         reason="Cerita personal dapat dikemas dengan konteks singkat untuk penonton baru.",
         search="career lessons interview mistakes personal story podcast",
         check="Jaga konteks pembicara. Judul hook ini contoh, bukan kutipan otomatis dari sumber."),
    dict(topic="culture", name="Indonesia untuk dunia", duration=30, hook="An everyday Indonesian tradition, explained in 30 seconds",
         angle="Kenalkan makanan, tradisi, atau kebiasaan Indonesia dengan konteks sederhana dalam subtitle Inggris.",
         reason="Sudut lokal bisa menjadi pembeda editorial bagi penonton yang belum mengenalnya.",
         search="Indonesian culture food traditions explained English",
         check="Jelaskan istilah lokal; jangan membuat stereotip atau generalisasi budaya."),
]
SOURCES = [
    dict(label="YouTube: jelajahi tren dan content gaps", url="https://support.google.com/youtube/answer/11962757?hl=en"),
    dict(label="YouTube: judul dan deskripsi terjemahan", url="https://support.google.com/youtube/answer/6289575?hl=en"),
]
