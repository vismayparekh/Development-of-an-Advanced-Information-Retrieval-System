import json
import re
import pymongo
from collections import defaultdict
from django.shortcuts import render, redirect
from .forms import DocumentForm
from .models import Document
from nltk.tokenize import word_tokenize
from nltk.stem import PorterStemmer
from PyPDF2 import PdfReader
from django.http import Http404, JsonResponse
from django.views.decorators.http import require_POST
from django.shortcuts import render
from .forms import SearchForm
from django.http import HttpResponse
from django.shortcuts import render, get_object_or_404
from .models import Document
from django.shortcuts import render, redirect
from django.core.validators import URLValidator
from django.core.exceptions import ValidationError
from django.shortcuts import redirect





# Initialize Porter Stemmer
porter = PorterStemmer()

# MongoDB connection
client = pymongo.MongoClient('mongodb://localhost:27017/')  #  MongoDB connection URL
db = client['DjongoProj']  # MongoDB database name
collection = db['Proj']  # MongoDB collection name

from django.contrib import messages

import uuid  #  for generating unique IDs

from django.conf import settings  #  to access global variables






def upload_document(request):
    success_message = None
    if request.method == 'POST':
        form = DocumentForm(request.POST, request.FILES)
        if form.is_valid():
            document = form.save(commit=False)
            document.save()
            success_message = "Document uploaded successfully!"
            # Parse and index 
            parse_and_index_document(document)
            return redirect('upload_document')  # Redirect to upload document 
    else:
        form = DocumentForm()
    return render(request, 'upload_document.html', {'form': form, 'success_message': success_message})






def parse_and_index_document(document):
    doc_id = document.id
    
    if document.file.name.endswith('.pdf'):
        content = parse_pdf(document.file)
    else:
        content = document.file.read().decode('utf-8')
    # Preprocess and create positional 
    index = create_positional_index(content, doc_id)
    # Save the index to MongoDB
    save_postings_mongodb(index)



def parse_pdf(file):
    pdf_text = ''
    pdf_reader = PdfReader(file)
    for page_num in range(len(pdf_reader.pages)):
        page = pdf_reader.pages[page_num]
        pdf_text += page.extract_text()
    return pdf_text

import re

def stem_word(word):
    # Define common plural suffixes
    plural_suffixes = ['s', 'es', 'ies']

    # Remove plural suffixes
    for suffix in plural_suffixes:
        if word.endswith(suffix):
            word = word[:-len(suffix)]
            break

    # Apply Porter stemming after removing plural suffix
    stemmed_word = porter.stem(word)

    return stemmed_word







def preprocess_text(text):
    # Tokenize text
    tokens = word_tokenize(text)

    # Filter out non-word tokens and empty strings
    word_tokens = [token for token in tokens if re.match(r'\w+', token) and token]

    # Apply custom stemming
    stemmed_tokens = [stem_word(token) for token in word_tokens]

    return stemmed_tokens






def create_positional_index(content, doc_id):
    index = defaultdict(lambda: defaultdict(list))
    terms = preprocess_text(content)
    for pos, term in enumerate(terms):
        index[term][str(doc_id)].append(pos + 1)
    return index






def find_query_in_document(query_words, postings, phrase_search=False):
    results = defaultdict(lambda: defaultdict(list))
    for word in query_words:
        if word in postings:
            for doc_id, positions in postings[word].items():
                results[doc_id][word].extend(positions)
    return results






def fetch_postings_from_mongodb():
    postings = {}
    cursor = collection.find({}, {'_id': 0})  # Exclude _id field
    for document in cursor:
        term = document['term']
        postings[term] = document['postings']
    return postings



def save_postings_mongodb(index):
    for term, postings in index.items():
        existing_doc = collection.find_one({'term': term})
        if existing_doc:
            # Update the existing document with new postings
            for doc_id, positions in postings.items():
                if doc_id in existing_doc['postings']:
                    existing_doc['postings'][doc_id].extend(positions)
                else:
                    existing_doc['postings'][doc_id] = positions
            collection.update_one(
                {'term': term},
                {'$set': {'postings': existing_doc['postings']}}
            )
        else:
            # Insert a new document if it doesn't exist
            collection.insert_one({'term': term, 'postings': postings})
            


def multiple_term_search(request):
    if request.method == 'POST':
        form = SearchForm(request.POST)
        if form.is_valid():
            query = form.cleaned_data['query']
            phrase_search = '+' not in query
            query_words = query.split('+') if '+' in query else [query]
            preprocessed_query = preprocess_text(' '.join(query_words))
            postings = fetch_postings_from_mongodb()
            search_results = find_query_in_document(preprocessed_query, postings, phrase_search)
            
            # Check if search results are empty
            if not search_results:
                return JsonResponse({'message': 'No Results Found'})
            
            return JsonResponse(search_results)
    else:
        form = SearchForm()
    return render(request, 'multiple_term_search.html', {'form': form})





def search_documents(request):
    if request.method == 'POST':
        form = SearchForm(request.POST)
        if form.is_valid():
            query = form.cleaned_data['query']
            validate = URLValidator()
            try:
                validate(query)  # Check if the query is a valid URL
                return redirect(query)  # Redirect to the URL
            except ValidationError:
                pass  # Continue with the normal search if it's not a valid URL

            phrase_search = '+' not in query
            query_words = query.split('+') if '+' in query else [query]
            preprocessed_query = preprocess_text(' '.join(query_words))
            postings = fetch_postings_from_mongodb()
            search_results = find_query_in_document(preprocessed_query, postings, phrase_search)

            # Store search results in session
            request.session['search_results'] = search_results
            request.session['search_terms'] = query_words

            # Check if search results are empty and handle accordingly
            if not search_results:
                messages.error(request, 'No Results Found')
                return render(request, 'search.html', {'form': form, 'message': 'No Results Found'})  # Stay on the same page

            return redirect('search_results')
    else:
        form = SearchForm()
    return render(request, 'search.html', {'form': form})






def search_results(request):
    search_results = request.session.get('search_results', {})
    document_details = {}
    for doc_id, details in search_results.items():
        try:
            document = Document.objects.get(id=doc_id)
            # Include the document's title along with other details
            document_details[doc_id] = {
                'positions': details,
                'title': document.title  
            }
        except Document.DoesNotExist:
            document_details[doc_id] = {
                'positions': [],
                'title': "Document not found"
            }

    return render(request, 'search_results.html', {
        'results': document_details
    })




def highlight_terms(text, terms):
    """Highlights search terms in the text."""
    for term in terms:
        print("Term before escaping:", term)  # Debug output
        term = re.escape(term)
        print("Term after escaping:", term)  # Debug output
        regex = re.compile(r'(\b' + term + r'\b)', re.IGNORECASE)
        text = regex.sub(r'<mark>\1</mark>', text)
        print("Text after substitution for term:", term)  # Debug output
    return text


def view_document(request, doc_id):
    document = get_object_or_404(Document, id=doc_id)
    search_terms = request.session.get('search_terms', [])
    
    try:
        pdf = PdfReader(document.file)
        text = ""
        for page in pdf.pages:
            text += page.extract_text()
        highlighted_text = highlight_terms(text, search_terms)
        
        return render(request, 'view_document.html', {
            'document_title': document.title,
            'document_text': highlighted_text,
            'search_terms': search_terms  # Pass the search terms to the template
        })
    except Exception as e:
        return HttpResponse(str(e), status=500)
