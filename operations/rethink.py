# -*- coding: utf-8 -*-

"""
## RETHINKDB
# Convert old rethinkdb schema
# into new cool and fancy json automatic documents
"""

from __future__ import absolute_import
import logging
from restapi.resources.services.rethink import RethinkConnection, RDBquery
from restapi import get_logger
from rethinkdb import r
from rethinkdb.net import DefaultCursorEmpty
from datetime import datetime
from elasticsearch import Elasticsearch
from confs.config import args

ES_HOST = {"host": "el", "port": 9200}
EL_INDEX = "autocomplete"
STEPS = {}

logger = get_logger(__name__)
logger.setLevel(logging.DEBUG)

TESTING = False

# Tables
t1 = "stepstemplate"
t2 = "steps"
t3 = "stepscontent"
t4 = "docs"
tin = "datakeys"
t2in = "datavalues"
t3in = "datadocs"

# Connection
RethinkConnection()
# Query main object
query = RDBquery()

######################
# Parameters
if args.rm:
    logger.info("Remove previous data")
    tables = query.list_tables()
    if tin in tables:
        query.get_query().table_drop(tin).run()
    if t2in in tables:
        query.get_query().table_drop(t2in).run()
    if t3in in tables:
        query.get_query().table_drop(t3in).run()


#################################
# MAIN
#################################
def convert_schema():
    """ Do all ops """

    ######################
    # Make tests
    if TESTING:
        test_el()
        test_query()

    ######################
    # Conversion from old structure to the new one
    tables = query.list_tables()

    if tin not in tables:
        convert_submission()
    if t2in not in tables:
        convert_search()
    if t3in not in tables:
        convert_docs()

    # check_indexes(t2in)

    convert_pending_images()

#################################
#################################


def convert_pending_images():
    """ Find images not linked to documents """

    print("DEBUG")
    exit(1)


def split_and_html_strip(string):
    """ Compute words from transcriptions """
    words = []
    START = '<'
    END = '>'
    skip = False
    word = ""
    for char in string:
        if char == START:
            skip = True
            continue
        elif char == END:
            skip = False
            continue
        if skip:
            continue
        if char.isalpha():
            word += char
        elif word != "" and len(word) > 3:
            words.append(word)  # word.lower())
            word = ""

    return set(words)


def convert_docs():
    """ Convert Data needed for search """
    qt1 = query.get_table_query(t4)
    qtin = query.get_table_query(t3in)

    pkey = 'record'
    q = query.get_query()

    if t3in in list(q.table_list().run()):
        q.table_drop(t3in).run()
    q.table_create(t3in, primary_key=pkey).run()
    logger.info("Startup table '%s'" % t3in)

    # Query
    res = qt1.group('recordid').order_by('code').run()
    key = 'transcriptions'
    for record, rows in res.items():
        images = []
    # Check images
        for row in rows:
            if key in row:
    # Fix transcriptions
                words = set()
                for trans in row[key]:
                    words = words | split_and_html_strip(trans)
                row[key+'_split'] = list(words)
            images.append(row)

        # Insert
        qtin.insert({pkey: record, 'images': images}).run()
        logger.info("Insert of record '%s'" % record)


def convert_search():
    """ Convert Data needed for search """
    qt1 = query.get_table_query(t3)
    qt2 = query.get_table_query(tin)
    qtin = query.get_table_query(t2in)

    pkey = 'record'
    q = query.get_query()

    if t2in in list(q.table_list().run()):
        q.table_drop(t2in).run()
    q.table_create(t2in, primary_key=pkey).run()
    logger.info("Startup table '%s'" % t2in)

    # Query
    res = qt1.group('recordid').order_by('step').run()

    # Elasticsearch magic
    print("Elasticsearch and indexes")
    es = Elasticsearch(hosts=[ES_HOST])
    es.indices.delete(index=EL_INDEX, ignore=[400, 404])
    es.indices.create(index=EL_INDEX, ignore=400)
    #es.indices.refresh(index=EL_INDEX)

    for record, rows in res.items():
        steps = []
        title = None

        for row in rows:

            # Compose back the elements...
            index = 0
            elements = []
            for myhash in row['hashes']:
                # Query with lambda. COOL!
                cursor = qt2.filter(
                    lambda x: x['fields']['original_hash'].contains(myhash)
                    ).run()
                fields = []

                try:
                    fields = cursor.next()['fields']
                except DefaultCursorEmpty:
                    logger.warning("No original hash for '%s'" % myhash)

                for field in fields:
                    if field['original_hash'] == myhash:
                        value = None
                        try:
                            value = row['values'][index]
                        except:
                            pass
                        elements.append({
                            'name': field['name'],
                            'position': field['position'],
                            'hash': field['original_hash'],
                            'value': value,
                        })
                        if field['position'] == 1:
                            title = value
                        break


                index += 1

            # Create a sane JSON to contain all the data for one step
            steps.append({
                'step': row['step'],
                # Extra info
                'latest_db_info': {
# WHAT ABOUT TIMESTAMP CONVERSION ALSO?
                    'timestamp': row['latest_timestamp'],
                    'ip': row['latest_ipaddress'],
                    'user_id': row['user'],
                },
                'data': elements,
            })

# PLUG ELASTICSEARCH SOMEWHERE IN HERE
        doc = {
            'category': STEPS[row['step']],
            'text': title,
            'timestamp': datetime.now(),
        }
# TO FIX?
        #print(doc)
        es.index(index=EL_INDEX, doc_type='normal', body=doc)
        #print("DEBUG EXIT"); exit(1)


        # Save the record
        qtin.insert({'record': record, 'steps': steps}).run()
        logger.info("Worked off document '%s'" % record)

    # # Create indexes
    # indexes = ['record']
    # existing_indexes = list(qtin.index_list().run())
    # for index in indexes:
    #     if index not in existing_indexes:
    #         qtin.index_create(index).run()
    #         logger.info("Added index '%s'" % index)


def check_indexes(table):

    q = query.get_table_query(table)
    existing_indexes = list(q.index_list().run())
    for index in existing_indexes:
        print(list(q.index_status(index).run()))


def convert_submission():
    """ Convert schema for Steps Submission """

    qt1 = query.get_table_query(t1)
    qt2 = query.get_table_query(t2)
    qtin = query.get_table_query(tin)
    qtin.delete().run()

    # DO
    data = qt1.group("step").run()
    for step in sorted(list(data)):
        new = {"step": None, "fields": None}
        myfilter = {'step': step}
        logger.info("*** STEP: %s" % step)

        # Single step elements
        element = list(qt2.filter(myfilter).run()).pop()
        new['step'] = {"num": step, "name": element['label'],
                       "desc": element['description']}

        # Singles steps fields
        element = []
        fields = list(qt1.filter(myfilter).run())
        sorted_fields = sorted(fields, key=lambda k: k['position'])
        for row in sorted_fields:
            if 'extra' not in row:
                row['extra'] = None

            element.append({
                "name": row['field'],
                "position": row['position'],
                "required": row['required'],
                "type": row['type'],
                "options": row['extra'],
                "original_hash": row['hash'],
            })

        # A whole step
        new["fields"] = element

        # INSERT
        logger.debug("To insert!\n%s" % new)
        qtin.insert(new).run()
        logger.info("Added row")
        tmp = new['step']
        STEPS[tmp['num']] = tmp['name']
    print(STEPS)


def test_query():
    """ test queries on rdb """
    # q = query.get_table_query(t2in)
    q = query.get_table_query(t3in)

    # cursor = q \
    #     .concat_map(
    #         lambda doc:
    #             doc['images'].has_fields({'transcriptions': True}).concat_map(
    #                 lambda image: image['transcriptions_split'])) \
    #     .distinct() \
    #     .run()

    cursor = q \
        .concat_map(
            lambda doc: doc['images'].has_fields(
                {'transcriptions': True}).map(
                    lambda image: {
                        'word': image['transcriptions_split'],
                        'record': doc['record'],
                    }
                )).distinct() \
        .filter(lambda mapped: mapped['word'].contains('grati')) \
        .run()

    # print(len(list(cursor)))
    # exit(1)
    for obj in cursor:
        print("TEST", obj)
        exit(1)
    exit(1)

    # # http://stackoverflow.com/a/34647904/2114395
    # cursor = q \
    #     .concat_map(
    #         lambda doc: doc['steps']
    #         .concat_map(lambda step: step['data']
    #                     .concat_map(lambda data:
    #                     [{'record': doc['record'], 'step': data}]))) \
    #     .filter(lambda doc:
    #             doc['step']['value'].match('mog').
    #             and_(doc['step']['name'].match('Numero de page'))) \
    #     .run()

    # for obj in cursor:
    #     print("TEST", obj)
    #     exit(1)

# #TEST1
#     cursor = q \
#         .concat_map(
#             lambda x: x['steps']['data'].map(
#                 lambda item: item['value'])
#         ) \
#         .run()
#     for obj in cursor:
#         print("TEST", obj)
#         exit(1)
#     print(list(cursor))
#     exit(1)

#WORKING FOR RECOVERING DATA
    cursor = q \
        .concat_map(r.row['steps']) \
        .filter(
            lambda row: row['step'] == 3
            ) \
        .concat_map(r.row['data']) \
        .filter(
            lambda row: row['position'] == 1
        ).pluck('value').distinct()['value'].run()
    print(list(cursor))


def test_el():
    print("TEST")
    es = Elasticsearch(hosts=[ES_HOST])
    print(es)

    # doc = {
    #     'author': 'kimchy',
    #     'text': 'Elasticsearch: cool. bonsai cool.',
    #     'timestamp': datetime.now(),
    # }
    # res = es.index(index="test-index", doc_type='tweet', id=1, body=doc)
    # print(res['created'])

    # Note:
    # Refresh indices at login startup!!!
    es.indices.refresh(index="test-index")

    res = es.get(index="test-index", doc_type='tweet', id=1)
    print(res['_source'])

    #es.search(index='posts', q='author:"Benjamin Pollack"')

    exit(1)
