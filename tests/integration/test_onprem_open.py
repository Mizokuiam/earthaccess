import logging
import random

import earthaccess
import magic
import pytest
from earthaccess import Auth, DataCollections, DataGranules, Store

from .sample import get_sample_granules

logger = logging.getLogger(__name__)

daacs_list = [
    {
        "short_name": "NSIDC",
        "collections_count": 50,
        "collections_sample_size": 3,
        "granules_count": 100,
        "granules_sample_size": 2,
        "granules_max_size_mb": 100,
    },
    {
        "short_name": "GES_DISC",
        "collections_count": 100,
        "collections_sample_size": 2,
        "granules_count": 100,
        "granules_sample_size": 2,
        "granules_max_size_mb": 130,
    },
]


def supported_collection(data_links):
    return all("podaac-tools.jpl.nasa.gov/drive" not in url for url in data_links)


@pytest.mark.parametrize("daac", daacs_list)
def test_earthaccess_can_open_onprem_collection_granules(daac):
    """Tests that we can download cloud collections using HTTPS links."""
    daac_shortname = daac["short_name"]
    collections_count = daac["collections_count"]
    collections_sample_size = daac["collections_sample_size"]
    granules_count = daac["granules_count"]
    granules_sample_size = daac["granules_sample_size"]
    granules_max_size = daac["granules_max_size_mb"]

    collection_query = DataCollections().data_center(daac_shortname).cloud_hosted(False)
    hits = collection_query.hits()
    logger.info(f"Cloud hosted collections for {daac_shortname}: {hits}")
    collections = collection_query.get(collections_count)
    assert len(collections) > collections_sample_size
    # We sample n cloud hosted collections from the results
    random_collections = random.sample(collections, collections_sample_size)
    logger.info(f"Sampled {len(random_collections)} collections")

    for collection in random_collections:
        concept_id = collection.concept_id()
        granule_query = DataGranules().concept_id(concept_id)
        total_granules = granule_query.hits()
        granules = granule_query.get(granules_count)
        assert len(granules) > 0, "Could not fetch granules"
        assert isinstance(granules[0], earthaccess.DataGranule)
        data_links = granules[0].data_links()
        if not supported_collection(data_links):
            logger.warning(f"PODAAC DRIVE is not supported at the moment: {data_links}")
            continue
        granules_to_open, total_size_cmr = get_sample_granules(
            granules,
            granules_sample_size,
            granules_max_size,
            round_ndigits=2,
        )
        if len(granules_to_open) == 0:
            logger.debug(
                f"Skipping {concept_id}, granule size exceeds configured max size"
            )
            continue
        logger.info(
            f"Testing {concept_id}, granules in collection: {total_granules}, "
            f"download size(MB): {total_size_cmr}"
        )

        store = Store(Auth().login(strategy="environment"))
        # We are testing this method
        fileset = store.open(granules_to_open)

        assert isinstance(fileset, list)

        # we test that we can read some bytes and get the file type
        for file in fileset:
            if not isinstance(file, Exception):
                logger.info(f"File type:  {magic.from_buffer(file.read(2048))}")
            else:
                logger.warning(f"File could not be open: {file}")
