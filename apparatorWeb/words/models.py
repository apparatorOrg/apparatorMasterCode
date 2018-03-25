# -*- coding: utf-8 -*-
from __future__ import unicode_literals, division
from django.utils.encoding import python_2_unicode_compatible
from django.db import models, connection
import nltk
from nltk.corpus import names, stopwords
from nltk import word_tokenize, FreqDist, RegexpTokenizer
from django.db.models import Avg, Sum

@python_2_unicode_compatible
class WordQuerySet(models.QuerySet):
    def __str__(self):
        return self.title

    def get_words(self, limit):
        words = self.all()[:limit]
        return words

    def get_words_and_frequencies(self, limit):
        words_and_frequencies = {}
        words = self.all()[:limit]
        for word in words:
            words_and_frequencies[word] = {'word frequency': word.get_word_frequency_stats().get('frequency__sum'),
                                           'reviews with word': word.get_word_review_frequency(),
                                           'word rating': word.get_word_rating().get('rating__avg')}
        return words_and_frequencies

class Word(models.Model):
    word = models.CharField(max_length=128, null=True)
    tag = models.CharField(max_length=128, null=True)


    def get_word_frequency_stats(self):
        frequency = ReviewWord.objects.filter(word=self.pk).aggregate(Sum('frequency'), Avg('frequency'))
        return frequency

    def get_word_review_frequency(self):
        frequency = ReviewWord.objects.filter(word=self.pk).count()
        return frequency

    def get_word_rating(self):
        rating = Review.reviews.filter(words__pk=self.pk).aggregate(Avg('rating'))
        return rating

    words = WordQuerySet.as_manager()

@python_2_unicode_compatible
class ReviewQuerySet(models.QuerySet):

    def __str__(self):
        return self.title

    def get_word_frequencies(self, limit):
        tokens = []
        reviews = self.all()[:limit]
        for review in reviews:
            # tokenize while removing punctuations and stop words - this should be stored in the db as it's the slow part
            for token in RegexpTokenizer(r'\w+').tokenize(review.review):
                if token.lower() not in stopwords.words('english'):
                    tokens.append(token.lower())

        freq_dist = FreqDist(tokens)
        return freq_dist

    def get_reviews_words(self, limit):
        #### The first two lines ignore UTF due to conversion errors #####
        #### This is required for SQLLITE and should be deprecated   #####
        connection.cursor()
        connection.connection.text_factory = lambda x: unicode(x, "utf-8", "ignore")
        #### end of part to ignore ####

        # returns a dictionary with key review id and value list of words

        words = {}  # should be a dictionary with 1) review id 2) list of words
        reviews = self.all()[:limit]
        # tokenize while removing punctuations and stop words - this should be stored in the db as it's the slow part
        for review in reviews:
            tokens = []
            for token in RegexpTokenizer(r'\w+').tokenize(review.review):
                if token.lower() not in stopwords.words('english'): #add all languages
                    tokens.append(token.lower())
                words[review.id] = tokens
        return words

    def populate_review_words(self, reviews_words):
        # !ASSUMES REVIEWS ARE PROCESSED ONCE!
        # takes a dictionary with {review_id, [words]} and populates the words reviews many to many database
        # 1. checks which words exist in the db
        # 2. if a word doesn't exist, adds it to the db and adds many to many relationship with the review id and
        #    frequency 1
        # 3. if a word exists checks if it exists for the current review
        # 4. if it exists for the current review, increment frequency by 1
        # 5. if it doesn't exist for the current review, create a many to many relationship and set frequency to 1

        for key, review_words in reviews_words.items(): #review_words will be a dictionary item
            existing_review = Review.reviews.get(pk=key)
            for word in review_words:
                try:
                    #check if word already exists
                    existing_word = Word.objects.get(word=word)
                    try:
                        #if word exists, check if there's a relationship established between word and review
                        word_review_relationship = ReviewWord.objects.get(word=existing_word,
                                                                          review=existing_review)
                        #if relationship established, increment frequency counter by one
                        new_frequency = word_review_relationship.frequency + 1
                        word_review_relationship.frequency = new_frequency
                        word_review_relationship.save()

                    except word_review_relationship.DoesNotExist:
                        #if word exists but relationship doesn't exist, establish one, and set frequency counter to 1
                        word_review_relationship = ReviewWord(review=existing_review, word=existing_word, frequency=1)
                        word_review_relationship.save()


                except Word.DoesNotExist:
                    # if word doesn't exist create the word, establish relationship, and set frequency to 1
                    new_word = Word.objects.create(word=word, tag=word)
                    new_word.save()
                    word_review_relationship = ReviewWord(review=existing_review, word=new_word, frequency=1)
                    word_review_relationship.save()

        return True



@python_2_unicode_compatible
class Review(models.Model):
    id = models.AutoField(primary_key=True)
    words = models.ManyToManyField(Word, through="ReviewWord")
    store_front = models.CharField(max_length=2)
    app_version = models.CharField(max_length=32)
    last_modified = models.DateTimeField('date published')
    nickname = models.CharField(max_length=128)
    rating = models.DecimalField(max_digits=3, decimal_places=2)
    title = models.CharField(max_length=255)
    review = models.TextField()
    edited = models.NullBooleanField()
    source = models.CharField(max_length=16, null=True)

    # app_id foreign key

    def __str__(self):
        return self.title

    def get_reviews_count(self, app_id, date_start, date_end):                  # add = today()
        return "will return number of reviews for app id in a given date range"

    # returns a list of words in review
    def get_review_words(self):
        review = self.review
        tokens = word_tokenize(review)
        return tokens

    # returns a list of words in review without stop words
    def get_clean_review_words(self):
        stop_words = set(stopwords.words("english"))
        filtered_review = []
        for w in self.get_review_words():
            if w not in stop_words:
                filtered_review.append(w)
        return filtered_review


    def get_word_rating(self, word, app_id, date_start, date_end):
        return "will return the average rating of the word in a given date range if from app (otherwise will simulate)"

    def get_word_frequency(self, word, app_id, date_start, date_end):
        return "will return the number of reviews in which this word appears in a given date range"

    reviews = ReviewQuerySet.as_manager()



class ReviewWord(models.Model):
    review = models.ForeignKey(Review, on_delete=models.CASCADE)
    word = models.ForeignKey(Word, on_delete=models.CASCADE)
    frequency = models.IntegerField(null=True)