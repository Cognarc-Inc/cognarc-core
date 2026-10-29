"""以反射取得資料表定義；schema 的唯一來源是 migration（原生 SQL），不在程式裡重複定義。"""

from sqlalchemy import Connection, MetaData, Table


def reflect_table(conn: Connection, qualified_name: str) -> Table:
    schema, name = qualified_name.split(".", 1)
    return Table(name, MetaData(schema=schema), autoload_with=conn)
