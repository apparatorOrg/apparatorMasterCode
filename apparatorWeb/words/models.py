# -*- coding: utf-8 -*-
from __future__ import unicode_literals, division
from django.utils.encoding import python_2_unicode_compatible
from django.db import models, connection
import nltk
from nltk.corpus import names, stopwords
from nltk import word_tokenize, FreqDist, RegexpTokenizer
from django.db.models import Avg, Sum, Prefetch, Count
import datetime, json, urllib, urllib2, requests

@python_2_unicode_compatible
class WordQuerySet(models.QuerySet):

    def __str__(self):
        return self.word

    def get_words(self, limit):
        words = self.all()[:limit]
        return words

    def get_word_stats(self, from_date, to_date, page=1, rows_per_page=50):
        # type: (date, date, int, int) -> object
        """

        :param from_date: start date
        :param to_date:  end date
        :param page: page views
        :param rows_per_page: number of rows presented per page
        :return: querySet object collection, each object is a dictionary with word, avg_rating, frequency

        TODO: secure pagination
        TODO: add dynamic sorting
        TODO: add week, month, day to review database so we can cheaply trunc_date through ORM
        """

        # this is probably doing nothing
        reviews_queryset = Review.reviews.filter(
                last_modified__range=[from_date, to_date]).order_by('last_modified')

        everything = self.filter(
                review__last_modified__range=[from_date, to_date]).prefetch_related(Prefetch(
                'review_set', queryset=reviews_queryset)).values('word').annotate(
                avg_rating=Avg('review__rating'), frequency=Count(
                'review__rating')).order_by(
                '-frequency')[page*rows_per_page-rows_per_page:page*rows_per_page]

        return everything

    def get_words_and_frequencies(self, from_date, to_date):
        """
        DEPRECATE: Not that interesting given "get_word_stats" is far more efficient
        :param from_date:
        :param to_date:
        :return:
        """
        words_and_frequencies = {}
        # words = self.all()[:limit]
        words = self.filter(review__last_modified__range=(from_date, to_date))
        if not words:
            return {1: {"nothing baby"}}
        for word in words:
            words_and_frequencies[word] = {'word frequency': word.get_word_frequency_stats(from_date, to_date).get('frequency__sum'),
                                           'reviews with word': word.get_word_review_frequency(from_date, to_date),
                                           'word rating': word.get_word_rating(from_date, to_date).get('rating__avg')}
        return words_and_frequencies

@python_2_unicode_compatible
class Word(models.Model):
    word = models.CharField(max_length=128, null=True)
    tag = models.CharField(max_length=128, null=True)

    def __str__(self):
        return self.word

    def get_word_frequency_stats(self, from_date, to_date):
        frequency = ReviewWord.objects.filter(word=self.pk,review__last_modified__range=(from_date, to_date)).aggregate(
            Sum('frequency'), Avg('frequency'))
        return frequency

    def get_word_review_frequency(self, from_date, to_date):
        frequency = ReviewWord.objects.filter(word=self.pk,review__last_modified__range=(from_date, to_date)).count()
        return frequency

    def get_word_rating(self, from_date, to_date):
        rating = Review.reviews.filter(words__pk=self.pk,last_modified__range=(from_date, to_date)).aggregate(
            Avg('rating'))
        return rating

    words = WordQuerySet.as_manager()


@python_2_unicode_compatible
class ReviewQuerySet(models.QuerySet):

    def __str__(self):
        return self.title

    def get_everything(self, from_date, to_date):
        #everything = self.filter(last_modified__range=(from_date, to_date)).prefetch_related('words')
        #everything = self.filter(last_modified__range=(from_date, to_date)).select_related('words')
        #return everything
        pass

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

    def get_reviews_from_apple_app_store(self, app_id='510855668', page='1', country_code='us'):
        """

        :param app_id: Apple app store App ID
        :param page: gets values 1-10, >10 will break method
        :param country_code: must be an Apple country code in which the app has activity.
        :return: json data of 50 reviews (per page). Also includes App meta data. Total up to 10 pages (500 last revs)

        TODO: error handling
        TODO: iTunesConnect, find login URL and also use this: https://itunesconnect.apple.com/WebObjects/iTunesConnect.woa/ra/apps/510855668/platforms/ios/reviews?sort=REVIEW_SORT_ORDER_MOST_RECENT
        More info here: https://github.com/fastlane/fastlane/issues/9824
        """
        url = 'https://itunes.apple.com/'+country_code+'/rss/customerreviews/id='+str(app_id)+'/sortBy=MostRecent/page='+str(page)+'/json'
        response = urllib.urlopen(url)
        data = json.loads(response.read())
        return data

    def get_reviews_from_iTunesConnect(self, app_id, username, password, page='1'):
        """

        :param app_id: Apple app ID
        :param username: Apple iTunesConnect account full email username
        :param password: Apple iTunesConnect account password
        :param page: which page of the reviews should we look at? Unlimited pages; 100 reviews per page.
        :return: json data with all reviews

        TODO: Iterate through pages until bumping into one of the last 10 reviews that exist in the DB
        TODO: When done iterating, load new reviews into db
        TODO: edited is true, update row instead of adding one.
        """

        login_url = 'https://idmsa.apple.com/appleauth/auth/signin' # 'https://itunesconnect.apple.com/WebObjects/iTunesConnect.woa'
        data_url = 'https://itunesconnect.apple.com/WebObjects/iTunesConnect.woa/ra/apps/510855668/platforms/ios/reviews?sort=REVIEW_SORT_ORDER_MOST_RECENT&index='+str(int(page)*100-100)

        creds = {
            'accountName': username,
            'password': password,
            'rememberMe': False,
        }
        headers = {
            'Content-Type':'application/json',
            'X-Apple-Widget-Key':'22d448248055bab0dc197c6271d738c3',
            'User-Agent':'Mozilla/5.0 (Windows NT 6.3; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/48.0.2564.116 Safari/537.36',
            'Accept':'application/json',
            'Referrer':'https://idmsa.apple.com',
        }

        #
        with requests.Session() as session:
            post = session.post(login_url, json=creds, headers=headers)

            # TODO: this should be in a while loop, loop through pages until a review ID is identified / error / null
            response = session.get(data_url)
            if response.ok:
                json_response = json.loads(response.text)

            reviews = []
            # TODO: get recent reviews and store in a var here (so we run the query only once).

            for review in range(0, 100):
                app_store_review_id = json_response['data']['reviews'][review]['value']['id']
                title = json_response['data']['reviews'][review]['value']['title']
                rating = json_response['data']['reviews'][review]['value']['rating']
                content = json_response['data']['reviews'][review]['value']['review']
                author = json_response['data']['reviews'][review]['value']['nickname']
                version = json_response['data']['reviews'][review]['value']['appVersionString']
                store_front = json_response['data']['reviews'][review]['value']['storeFront']
                last_modified = json_response['data']['reviews'][review]['value']['lastModified']
                helpful_views = json_response['data']['reviews'][review]['value']['helpfulViews']
                total_views = json_response['data']['reviews'][review]['value']['totalViews']
                edited = json_response['data']['reviews'][review]['value']['edited']

                # TODO: add condition to check if review already exists (develop get last 10 review IDs method)
                # TODO: If app_store_review_id in get_recent_reviews(count=10, app_id) or get recent is null
                reviews.append({
                    'id': app_store_review_id,
                    'title': title,
                    'rating': rating,
                    'content': content,
                    'author': author,
                    'version': version,
                    'store_front': store_front,
                    'last_modified': last_modified,
                    'helpful_views': helpful_views,
                    'total_views': total_views,
                    'edited': edited,
                })

        # TODO: db insert or update (depending on 'edited')

        return reviews

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
        # "will return number of reviews for app id in a given date range
        pass

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