from neo4j import Driver
from utils import ts, log
from db import neo4j

CLIENT: Driver.session
LOGGER = None


def init():
    global CLIENT, LOGGER
    CLIENT = neo4j.DRIVER.session()
    LOGGER = log.get_logger("mgdao")
#
#
# def get_movies_to_update_itunes():
#     results = client.run("MATCH (movie:Movie{active:true, status:\"APPROVED\"})-[:name]-(name:Multilingual) "
#                          "WHERE NOT (movie)-[:vod]-(:Vod{type:\"ITUNES\"}) "
#                          "RETURN movie.uuid as uuid, name.zhHK as name_chi, name.enGB as name_eng, "
#                          "movie.openDate as open_date, \"\" as vod_uuid, 0 as vod_createAt "
#                          "UNION ALL "
#                          "MATCH (movie:Movie{active:true, status:\"APPROVED\"})-[:name]-(name:Multilingual) "
#                          "MATCH (movie)-[:vod]-(vod:Vod{type:\"ITUNES\"}) "
#                          "WHERE NOT (vod.purchasePrice > 0 AND vod.rentalPrice > 0 "
#                          "AND vod.purchaseHdPrice > 0 AND vod.rentalHdPrice > 0) "
#                          "AND vod.edited = false "
#                          "RETURN movie.uuid as uuid, name.zhHK as name_chi, name.enGB as name_eng, "
#                          "movie.openDate as open_date, vod.uuid as vod_uuid, vod.createAt as vod_createAt")
#
#     return [Movie(**i.data()) for i in results]
#
#
#
# def create_vod(vod: Vod, movie_id: str):
#     # will raise RecursionError: maximum recursion depth exceeded while calling a Python object
#     # vod = re.sub(r'"(\w+)":', r'\1:', jsonpickle.dumps(vod, unpicklable=False))
#     vod_json = re.sub(r'\'(\w+)\':', r'\1:', str(vod.__dict__))
#     LOGGER.info(f"vod_json={vod_json}")
#
#     client.run("MATCH (movie:Movie{uuid: {uuid}}) "
#                f"CREATE (vod:Vod{vod_json}) "
#                f"MERGE (movie)-[:vod]->(vod) ",
#                {"uuid": movie_id})
#
#
# def link(vod_type, movie_id, vod_site_key):
#     results = client.run("MATCH (movie:Movie{uuid: {movie_id}}), (vod:Vod{type: {vod_type}, siteKey: {vod_site_key}}) "
#                          "MERGE (movie)-[:vod]->(vod) "
#                          "SET movie.active = true, movie.updateAt = {updateAt}, vod.active = true, vod.updateAt = {updateAt}"
#                          "RETURN movie.uuid as movie_id",
#                          {"vod_type": vod_type,
#                           "movie_id": movie_id,
#                           "vod_site_key": vod_site_key,
#                           "updateAt": ts.getUtcnowSeconds()
#                           })
#
#     # return the first one
#     for i in results:
#         LOGGER.info(i['movie_id'])
#         return i['movie_id']
#
#
# def update_vod(vod: Vod):
#     vod_json = re.sub(r'\'(\w+)\':', r'\1:', str(vod.__dict__))
#     # will raise RecursionError: maximum recursion depth exceeded while calling a Python object
#     # vod_json = re.sub(r'"(\w+)":', r'\1:', jsonpickle.dumps(vod, unpicklable=False))
#     LOGGER.info(f"vod_json={vod_json}")
#
#     results = client.run("MATCH (vod:Vod{uuid: {uuid}}) "
#                          f"SET vod = {vod_json} "
#                          "WITH vod "
#                          "MATCH (vod)--(movie:Movie) "
#                          "RETURN movie.uuid as movie_id ",
#                          {"uuid": vod.uuid})
#
#     # return the first one
#     for i in results:
#         LOGGER.info(i['movie_id'])
#         return i['movie_id']
#
#
# def find_vod_without_movie_info(vod_type):
#     results = client.run(
#         "MATCH (vod:Vod{type: {vod_type}, active: true})-[:vod]-(movie:Movie{active: true}) "
#         "MATCH (poster:Multilingual)-[:poster]-(movie)-[:synopsis]-(synopsis:Multilingual) "
#         "WHERE poster.zhHK = '' or poster.enGB = '' or synopsis.enGB = '' or synopsis.zhHK = '' or movie.duration < 1 or movie.openDate < 1 "
#         "RETURN vod "
#         "ORDER BY vod.createAt ASC",
#         {"vod_type": vod_type})
#
#     return [i['vod'] for i in results]
#
#
# # use once
# def find_poster(vod_type):
#     results = client.run(
#         "MATCH (vod:Vod{type: {vod_type}, active: true})-[:vod]-(movie:Movie{active: true})-[:poster]-(poster:Multilingual) "
#         "WHERE poster.zhHK =~ 'http.*image.anyplex.com.*' or poster.enGB =~ 'http.*image.anyplex.com.*' "
#         "RETURN vod.siteKey as vod_site_key, poster ",
#         {"vod_type": vod_type})
#
#     return [i.data() for i in results]
#
#
# def find_movie_name_by_id(movie_id):
#     results = client.run("MATCH (movie:Movie{uuid: {movie_id}})-[:name]-(name:Multilingual) RETURN name ",
#                          {"movie_id": movie_id})
#
#     # return the first one
#     for i in results:
#         LOGGER.info(i['name'])
#         return i['name']
#
#
# def find_vod_by_type_and_site_key(vod_type, site_key):
#     results = client.run(
#         "MATCH (vod:Vod{type: {vod_type}, siteKey: {site_key}}) RETURN vod ORDER BY vod.active DESC, vod.updateAt DESC",
#         {"vod_type": vod_type, "site_key": site_key})
#
#     # return the first one
#     for i in results:
#         LOGGER.info(i['vod'])
#         return i['vod']
#
#
# def find_vod_by_type_and_movie_id(vod_type, movie_id):
#     results = client.run(
#         "MATCH (vod:Vod{type: {vod_type}})--(:Movie{uuid: {movie_id}}) RETURN vod",
#         {"vod_type": vod_type, "movie_id": movie_id})
#
#     for i in results:
#         LOGGER.info(i['vod'])
#         return i['vod']
#
#
# def find_vod_by_type_and_active_movie_id(vod_type, movie_id, movie_status=[]):
#     results = client.run(
#         "MATCH (vod:Vod{type: {vod_type}, active: true})--(movie:Movie{uuid: {movie_id}, active: true}) "
#         "WHERE movie.status in {movie_status} "
#         "RETURN vod",
#         {"vod_type": vod_type, "movie_id": movie_id, "movie_status": movie_status})
#
#     return [i['vod'] for i in results]
#
#
# def create_or_update_setting(site_keys):
#     client.run("MERGE (setting:CronJobSetting{name: {name}}) "
#                "SET setting.hmvod_site_keys = {site_keys} ",
#                {"name": "itunes-cron", "site_keys": site_keys})
#
#
# def create_or_update_setting(vod_type, site_keys):
#     client.run("MERGE (setting:CronJobSetting{name: {name}, type: {vod_type}}) "
#                "SET setting.site_keys = {site_keys} ",
#                {"name": "itunes-cron", "vod_type": vod_type, "site_keys": site_keys})
#
#
# def get_hmvod_site_keys():
#     results = client.run("MATCH (setting:CronJobSetting{name: {name}}) "
#                          "RETURN setting.hmvod_site_keys as site_keys",
#                          {"name": "itunes-cron"})
#
#     # todo review
#     # return the first one
#     for i in results:
#         LOGGER.info(i['site_keys'])
#         return i['site_keys']
#
# # removing by setting active to false
# # return movie uuids
# def remove_vod_by_site_keys(vod_type: str, site_keys):
#     results = client.run("MATCH (vod:Vod{type: {type}, active: true})-[r:vod]-(movie:Movie) "
#                          "WHERE vod.siteKey in {site_keys} "
#                          "SET vod.updateAt = {updateAt}, vod.endAt = {updateAt}  "
#                          "DELETE r "
#                          "RETURN vod.uuid as vod_id, movie.uuid as movie_id",
#                          {"type": vod_type,
#                           "site_keys": site_keys,
#                           "updateAt": ts.getUtcnowSeconds()
#                           })
#
#     return [i['movie_id'] for i in results]
