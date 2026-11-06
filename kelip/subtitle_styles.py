"""Curated ASS subtitle styles, all using the existing 720×1280 canvas."""
SUBTITLE_STYLES = {
    'classic': {'label':'Klasik · default', 'description':'Putih tebal dengan outline hitam, seperti tampilan sebelumnya.',
                'ass':'Arial,42,&H00FFFFFF,&H000000FF,&H00101010,&H80000000,-1,0,0,0,100,100,0,0,1,3,1,2,45,45,220,1'},
    'bold_yellow': {'label':'Kuning tebal', 'description':'Teks kuning besar dengan outline hitam yang tegas.',
                'ass':'Arial,48,&H0000EFFF,&H000000FF,&H00101010,&H80000000,-1,0,0,0,100,100,0,0,1,4,1,2,45,45,220,1'},
    'boxed': {'label':'Kotak gelap', 'description':'Teks putih dengan latar gelap untuk gambar yang ramai.',
                'ass':'Arial,42,&H00FFFFFF,&H000000FF,&H40101010,&H40101010,-1,0,0,0,100,100,0,0,3,9,0,2,45,45,220,1'},
    'minimal': {'label':'Minimal', 'description':'Teks putih lebih kecil dan ringan dengan outline tipis.',
                'ass':'Arial,34,&H00FFFFFF,&H000000FF,&H00202020,&H80000000,0,0,0,0,100,100,0,0,1,2,0,2,55,55,220,1'},
}
