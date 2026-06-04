from langchain_core.tools import tool


# 以下 Tools 不执行任何逻辑、不返回任何内容，需要让 LLM 通过调用 Tool 来确定路由到对应的意图 intent
# 不在 Tool 里面直接执行逻辑是因为确定意图后，并不能保证全部所需 payload 都已完整，需要后续的判断/澄清后确定后再执行


@tool
def handoff2Reject() -> None:
    """
    Route to intent `reject`.

    Use this tool when the request is out of scope, unsafe, policy-violating, or
    clearly not supported by the current GeneralGraph capabilities. This tool is
    also appropriate when the user asks for an action unrelated to conversation,
    FR management, FR enrichment, FR feed recall/conflict handling, or current
    user self-inspection.
    """
    return


@tool
def handoff2Clarify() -> None:
    """
    Route to intent `clarify`.

    Use this tool when the request may be valid but the user's goal is still
    ambiguous, and you cannot reliably choose exactly one downstream intent yet.
    Typical cases include unclear target FR, unclear desired operation, or
    missing context that is required before even deciding the correct route.
    """
    return


@tool
def handoff2ConversationGraph() -> None:
    """
    Route to intent `conversation_graph`.

    Use this tool when the user wants to chat with, roleplay with, or continue a
    dialogue as a specific FigureAndRelation. This intent is for conversational
    interaction, not for editing FR data. The target FR should be known or can be
    clarified later if currently missing.
    """
    return


@tool
def handoff2FRBuildingGraph() -> None:
    """
    Route to intent `fr_building_graph`.

    Use this tool when the user wants to enrich, complete, or update a specific
    FigureAndRelation based on newly provided raw material, such as narrative
    text, facts, memories, or source content. This intent is for ingesting new
    material into FR-related memory structures, not for ordinary conversation.
    """
    return


@tool
def handoff2Whoami() -> None:
    """
    Route to intent `auth_whoami`.

    Use this tool when the user asks to inspect their own current account or
    identity information, such as who they are, which account is logged in, or
    what their current user profile is.
    """
    return


@tool
def handoff2FRAdd() -> None:
    """
    Route to intent `fr_add`.

    Use this tool when the user explicitly wants to create a new
    FigureAndRelation. The request should describe a new person or character to
    add, rather than asking to view, chat with, or enrich an existing FR.
    """
    return


@tool
def handoff2FRList() -> None:
    """
    Route to intent `fr_list`.

    Use this tool when the user wants to view, browse, or enumerate the current
    FigureAndRelation list, such as asking what FRs already exist or which roles
    are currently available.
    """
    return


@tool
def handoff2FRShow() -> None:
    """
    Route to intent `fr_show`.

    Use this tool when the user wants to inspect the profile, persona, or full
    context of a specific FigureAndRelation. This includes requests to view FR
    details, see a figure's current memory/persona, or examine a specific FR by
    id, name, or role.
    """
    return


@tool
def handoff2FRSyncFeeds() -> None:
    """
    Route to intent `fr_sync_feeds`.

    Use this tool when the user wants to synchronize fine-grained feeds into FR
    core fields, either for one specific FR or for all FRs. This is a
    summarization/synchronization action, not a recall or browsing action.
    """
    return


@tool
def handoff2FRFeedRecall() -> None:
    """
    Route to intent `fr_feed_recall`.

    Use this tool when the user wants to recall or retrieve previously stored
    fine-grained information related to a specific FR, usually by topic, memory
    cue, fact query, or semantic description. This intent is for searching stored
    FR feeds, not for starting a live conversation.
    """
    return


@tool
def handoff2FRConflictList() -> None:
    """
    Route to intent `fr_conflict_list`.

    Use this tool when the user wants to list pending conflicts for a specific
    FR, such as unresolved contradictory feed items or outstanding conflict
    records that still require review.
    """
    return


# todo: 后续加
# @tool
# def handoff2FRConflictResolve() -> None:
#     """
#     Route to intent `fr_conflict_resolve`.

#     Use this tool when the user wants to resolve an existing pending FR conflict,
#     including choosing how a conflict should be marked or settled. The target
#     conflict should be known or clarifiable from the conversation.
#     """
#     return
