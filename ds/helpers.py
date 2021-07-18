import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.orm.session import Session
from tqdm.notebook import tqdm

from couchers.config import config
from couchers.db import session_scope
from couchers.models import Cluster, Discussion


def get_table_columns(table):
    with session_scope() as session:
        query = session.query(table).limit(0)
        df = pd.read_sql(query.statement, query.session.bind)
        return list(df.columns)


def get_dataframe(table):
    with session_scope() as session:
        query = session.query(table)
        return pd.read_sql(query.statement, query.session.bind)


def update_community_description(node_id, description, overide_length_constraint=False):

    if len(description) > 500 and not overide_length_constraint:
        print(
            f"The description length is {len(description)}. The limit is 500 characters."
        )
        return

    with session_scope() as session:
        community = (
            session.query(Cluster).filter(Cluster.parent_node_id == node_id).one()
        )
        community.description = description
        name = community.name
        new_description = community.description
    print(f"The {name} community description has been updated to:\n{new_description}")


def get_incomplete_communities_df():
    with session_scope() as session:
        print("getting communities...")
        community_df = get_dataframe(Cluster).query("is_official_cluster == True")
        community_df["url"] = community_df.apply(
            lambda row: f"app.couchers.org/community/{row.parent_node_id}/{row.slugify_1}",
            axis=1,
        )
        result_df = community_df[
            ["id", "parent_node_id", "name", "url", "created"]
        ].copy()

        print("getting discussions...")
        discussion_df = get_dataframe(Discussion)

        result_df["has_discussions"] = result_df.id.apply(
            lambda x: _has_discussions(x, discussion_df)
        )

        tqdm.pandas(desc="getting properties for communities")
        (
            result_df["has_description_length"],
            result_df["has_main_page_length"],
            result_df["has_non_man_admin"],
        ) = zip(
            *result_df.parent_node_id.progress_apply(
                lambda x: _complete_community_properties(session, x)
            )
        )

        return result_df[
            ~(
                result_df.has_discussions
                & result_df.has_description_length
                & result_df.has_main_page_length
                & result_df.has_non_man_admin
            )
        ]


def _has_discussions(community_id, discussion_df):
    num_discussions = discussion_df.query(
        f"owner_cluster_id == {str(community_id)}"
    ).shape[0]
    return num_discussions > 0


def _complete_community_properties(session, community_node_id):
    community = (
        session.query(Cluster).filter(Cluster.parent_node_id == community_node_id).one()
    )
    return (
        len(community.description) > 100,
        len(community.main_page.versions[-1].content) > 100,
        _has_non_man_admin(community),
    )


def _has_non_man_admin(community):
    admins = community.admins.all()
    for admin in admins:
        if admin.gender not in ["Man", "Male"]:
            return True
    return False


def create_session():
    engine = create_engine(config["DATABASE_CONNECTION_STRING"])
    return Session(engine)
