python3 generate_grade_svgs.py

# Fix PDF timestamp to a constant so output is deterministic across runs.
# rsvg-convert uses Cairo, which respects SOURCE_DATE_EPOCH for PDF metadata.
export SOURCE_DATE_EPOCH=0

# Convert root SVG
for svg in *.svg; do
  base="${svg%.svg}"
  rsvg-convert -f pdf "$svg" -o "${base}.pdf"
  pandoc "$svg" -o "${base}.html"
done

# Convert per-grade SVGs in subdirectories
for dir in 9th 10th 11th 12th; do
  for svg in "$dir"/*.svg; do
    base="${svg%.svg}"
    rsvg-convert -f pdf "$svg" -o "${base}.pdf"
    pandoc "$svg" -o "${base}.html"
  done
done

# Sync to drive, mirroring directory structure
cp ./*.svg ./*.pdf ./*.html ~/mydrive/gradFlow/
for dir in 9th 10th 11th 12th; do
  mkdir -p ~/mydrive/gradFlow/"$dir"
  cp "$dir"/*.svg "$dir"/*.pdf "$dir"/*.html ~/mydrive/gradFlow/"$dir"/
done
