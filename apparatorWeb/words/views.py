# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from django.http import HttpResponse
from django.shortcuts import render
from .models import Review, Word



def index(request):
    #tokens = Review.objects.get(id=3).get_clean_review_words()
    # freq = Review.reviews.get_word_frequencies(500)
    # words = Review.reviews.get_reviews_words(100)
    words = Word.words.get_words_and_frequencies(1000)
    context = {'word_dict': words}
    return render(request, 'words/index.html', context)
    #return HttpResponse(words.items()) #most_common(10) will give just the most common sorted

def test(request):
    test = Review.reviews.populate_review_words(Review.reviews.get_reviews_words())
    return HttpResponse(test.items())

