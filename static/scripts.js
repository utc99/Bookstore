var goodreadsdata = 'No data';
var lastvote ='';
var clickedvote = '';
var currentbook = '';

//-------------------------------------------------------------------------
//Close 'Popup' windows when clicked outside of them(on transparent modal)
$(function (){
  $('.modal').on('click', function(event) {
    var className = event.target.className;
    if(className === 'modal' ){
      $(this).closest('.modal').hide();
      $('.active').removeClass('active');
    }
    //When in single search result page and stars rating is used, save last vote, reload total votes
    else if (event.target.parentElement.className === 'rating') {
      clickedvote = event.target.id;
      $('#' + clickedvote).addClass('active');
      update_rating(currentbook);

      //Fade out our rating, wait while server updates data and show new rating
      $('#ourrating').fadeOut( 5000);
      setTimeout(function(){
        APIcall(currentbook);
      }, 4000);
      $('#ourrating').fadeIn('slow');
    }
  });
});

//-------------------------------------------------------------------------
//Show detailed info of selected search result

$(function (){
  $('.search-element').click(function () {

    // Show loader, hide/clear old data
    $('.loader').show();
    $('#search_loader').hide();
    $('#search-bookpage-h3').html('');
    $('#result1').hide();
    $('#reviewsarea').hide();
    $('.all-reviews').hide();
    lastvote = '';

    //Show detailed results window
    document.getElementById('search-bookpage').style.display='block';

    var isbn = this.id;
    currentbook = isbn;

    //Form detailed data
    GetGoodreadsAPI(isbn);
    get_review_data(isbn);
    APIcall(isbn);
  });
});

//-------------------------------------------------------------------------
//Remove displayed rating if user want to vote again
$(function (){
  $('#stars').on('mouseenter', function() {
    $('.active').removeClass('active');
  });
});

//-------------------------------------------------------------------------
//Loader while signing in
$(function (){
  $('.signupbtn').click(function () {
    $('.loader').show();
    $('.loader').fadeOut(7000);
  });
});
//-------------------------------------------------------------------------
//Loader while searching
$(function (){
  $('.searchbtn').click(function () {
    $('.loader').show();
    $('.loader').fadeOut(7000);
  });
});

//-------------------------------------------------------------------------
//Submit review listener
$(function (){
  $('#submit_review').click(function () {
    $('.circle-loader').show();
    $('.circle-loader').addClass('load-complete');
    $('.checkmark').show();
    $('.circle-loader').fadeOut(3000);
    write_review($('#reviewcontent').val());
  });
});

//-------------------------------------------------------------------------
//If user left rating area without rating it again, display last rating

$(function (){
  $('#stars').on('mouseleave', function() {
    $('#' + lastvote).addClass('active');
  });
});

//-------------------------------------------------------------------------
//Get book's data using our API and form display window
function APIcall(isbn){

  var parameters = {
        isbn: isbn
    };
  $.getJSON(Flask.url_for('api', parameters))
  .done(function(data, textStatus, jqXHR) {

    //Hide loader and show book's data
    $('.loader').hide();
    $('#search-bookpage-h3').html(data.title);
    $('#goodreadsrating').html(goodreadsdata);
    $('#average_score').html(data.average_score.toFixed(2));
    $('#review_count').html(data.review_count);
    $('#author').html(data.author);
    $('#year').html(data.year);
    $('#isbn').html(data.isbn);
    $('#result1').show();
    $('#reviewsarea').show();
    $( '#ourrating' ).fadeIn( 'slow');
  });
}

//-------------------------------------------------------------------------
//Get book's data from Goodreads.com API
function GetGoodreadsAPI(isbn){

  var parameters = {
      isbn: isbn
  };
  $.getJSON(Flask.url_for('GoodreadsAPI'),parameters)
  .done(function(data) {
    if (data['status'] == 'No data'){
          goodreadsdata = 'No data';
    }
    else{
      goodreadsdata = data['average_rating'] + ' (' + data['work_ratings_count'] + ' votes)';
    }
  });
}

//-------------------------------------------------------------------------
// Update book's rating in a server
function update_rating(currentbook){

  // Update rating in a server
  $.postJSON( Flask.url_for('rate'), { rating: clickedvote, isbn: currentbook })

  .done(function(data) {
      if (data['status'] != 'Success'){
          alerts(data['status'], 'alert alert-danger');
      }
  });
  lastvote = clickedvote;
}

//-------------------------------------------------------------------------
//Update book's review in a server
function write_review(review_content){

  // Update rating in a server
  $.postJSON( Flask.url_for('submit_review'), { review: review_content, isbn: currentbook })

  .done(function(data) {
      if (data['status'] != 'Success'){
          alerts(data['status'], 'alert alert-danger');
      }
  });
}

//-------------------------------------------------------------------------
// Get review data for the book of all users
// Get all reviews for the book, if it's a current user's review, change star rating, display review's content
function get_review_data(isbn){

  $('#reviewcontent').val('');
  var  all_reviews_content ='';
  $.postJSON( Flask.url_for('reviews_data'), {isbn: isbn })

  .done(function(data) {
    if (data['status'] == 'Event(04). Report to administrator.'){
        alerts(data['status'], 'alert alert-danger');
    }
    else if (data['status'] != 'No reviews'){
      data.forEach(function(element) {
        if (element['user_id'] == 'ME') {
          lastvote = element['rating'];
          $('#' + element['rating']).addClass('active');

          if (element['review'] != 'EMPTY') {
            $('#reviewcontent').val(element['review']);
              $('.all-reviews').show();
            }
        }
        if (element['rating'] < 0){
          element['rating'] = 'No rating';
        }
        else {
           element['rating'] = element['rating'].toFixed(2);
        }
        if (element['review'] !== 'EMPTY') {
          //Dynamically form a list of reviews
          all_reviews_content  += '<div id=single_review>'
                              + '<div id=others_rating class="col-xs-4 col-sm-4 col-md-6 reviews_list">'
                              +    '<b>' + element['email'] + '</b>'
                              + '</div>'
                              + '<div id=others_rating class="col-xs-4 col-sm-4 col-md-6 reviews_list">'
                              +   '<b>' + element['rating'] + '</b>'
                              + '</div>'
                              + '<div id=review_itself>' + element['review'] + '</div>'
                              + '</div>';

          $('.all-reviews').show();
        }
      });
      $('#all_review_content').html(all_reviews_content);
    }
  });
}

//-------------------------------------------------------------------------
// Show notifications for the user after performed actions
function alerts(alertmsg, alertClass) {

  $('#alerts').html(alertmsg);
  $('#alerts').attr('class', alertClass);
  $('#alerts').fadeTo(2000, 500).slideUp(500, function() {
    $('#alerts').slideUp(500);
  });
}

//-------------------------------------------------------------------------
// Extend jquery, add JSON data support for jquerry post, 3rd party code
jQuery.extend({

  postJSON: function(url, data, callback, type) {
	// shift arguments if data argument was omited
    if (jQuery.isFunction(data)) {
  		type = type || callback;
  		callback = data;
  		data = {};
	  }
    return jQuery.ajax({
      'type': 'POST',
      'url': url,
      'contentType': 'application/json',
      'data': JSON.stringify(data),
      'dataType': 'json',
      'success': callback
	  });
  }
});