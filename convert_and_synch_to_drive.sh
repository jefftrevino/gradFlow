rsvg-convert -f pdf lwhs_course_selection.svg -o lwhs_course_selection.pdf
pandoc lwhs_course_selection.svg -o lwhs_course_selection.html
cp ./lwhs_course_selection.* ~/mydrive/gradFlow
