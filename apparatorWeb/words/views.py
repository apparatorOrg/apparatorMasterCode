# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from django.http import HttpResponse
from django.shortcuts import render
from .models import Review, Word
import datetime



def index(request):
    #tokens = Review.objects.get(id=3).get_clean_review_words()
    # freq = Review.reviews.get_word_frequencies(500)
    # words = Review.reviews.get_reviews_words(100)
    # words = Word.words.get_words_and_frequencies(datetime.date(2017, 9, 30),datetime.date(2017, 10, 2))
    # context = {'word_dict': words}

    # reviews = Review.reviews.get_everything(datetime.date(2017, 9, 30),datetime.date(2018, 10, 3))
    # context = {'reviews': reviews}
    # return render(request, 'words/reviews.html', context)

    words = Word.words.get_word_stats('2017-09-30', '2018-10-01', 1, 10)
    context = {'words': words}

    word_stats = {}

    #create aggregate and group by word id on app id


    return render(request, 'words/words.html', context)

    #return render(request, 'words/index.html', context)



def test(request):
    # test = Review.reviews.populate_review_words(Review.reviews.get_reviews_words()) #populate words based on reviews db

    """
    # MOVE THIS TO MODEL
    # Missing Title, last modified, and "edited"

    test = Review.reviews.get_reviews_from_apple_app_store(page=2)
    reviews = []
    for page in range(1, 6):
        json_response = Review.reviews.get_reviews_from_apple_app_store(page=page)
        for review in range(1, 51):
            app_store_review_id = json_response['feed']['entry'][review]['id']['label']
            title = json_response['feed']['entry'][review]['title']['label']
            rating = json_response['feed']['entry'][review]['im:rating']['label']
            content = json_response['feed']['entry'][review]['content']['label']
            author = json_response['feed']['entry'][review]['author']['name']['label']
            version = json_response['feed']['entry'][review]['im:version']['label']

            reviews.append({
                'id': app_store_review_id,
                'title': title,
                'rating': rating,
                'content': content,
                'author': author,
                'version': version,
            })

    return HttpResponse(reviews)
    """

    test = Review.reviews.get_reviews_from_iTunesConnect(app_id='510855668',username='dbenami@amazon.com', password='ucdsyzA9')
    return HttpResponse(test)
