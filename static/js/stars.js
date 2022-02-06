const ratingStars = [...document.getElementsByClassName("rating_star")];
function executeRating(stars) {
  const starClassActive = "fa fa-star fa-2x rating_star";
  const starClassInactive = "fa fa-star-o fa-2x rating_star";
  const starsLength = stars.length;
  let i;
  stars.map((star) => {
    star.onclick = () => {
      i = stars.indexOf(star);

      if (star.className===starClassInactive) {
        for (i; i >= 0; --i){
            stars[i].className = starClassActive;
        }
        document.getElementById("rate").value = stars.indexOf(star)+1;
      }
      else {
        for (i; i < starsLength; ++i){
            stars[i].className = starClassInactive;

        }
        document.getElementById("rate").value = stars.indexOf(star);
      }
    };
  });
}
executeRating(ratingStars);