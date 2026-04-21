python3 generate_grade_svgs.py
for svg in *.svg; do
  base="${svg%.svg}"
  rsvg-convert -f pdf "$svg" -o "${base}.pdf"
  pandoc "$svg" -o "${base}.html"
done
cp ./*.svg ./*.pdf ./*.html ~/mydrive/gradFlow
