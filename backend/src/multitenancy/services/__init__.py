"""multitenancy.services — orchestration over repositories + events + RPC.

Order of dependency:
    workspace_service →  WorkspaceRepository + CellRepository + events
    cell_service      →  CellRepository + CellMemberRepository + events +
                         multitenancy.provision_cell_schema() SQL function
"""
