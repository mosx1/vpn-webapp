from sqlalchemy import Column,Numeric, SMALLINT, BIGINT, TEXT, TIMESTAMP, BOOLEAN, CHAR, ForeignKeyConstraint, INTEGER, func, text
from sqlalchemy.ext.declarative import declarative_base

from connect import engine

Base = declarative_base()


class User(Base):

    __tablename__: str = 'users_subscription'

    telegram_id: Column = Column(BIGINT, primary_key=True)
    name: Column = Column(TEXT, nullable=True)
    exit_date: Column = Column(TIMESTAMP, nullable=False)
    action: Column = Column(BOOLEAN, nullable=False)
    server_link: Column = Column(TEXT, nullable=False)
    server_id: Column = Column(BIGINT, nullable=False)
    server_desired: Column = Column(CHAR, nullable=True)
    paid: Column = Column(BOOLEAN, nullable=False)
    protocol: Column = Column(BIGINT, nullable=False)
    statistic: Column = Column(TEXT, nullable=True)
    balance: Column = Column(Numeric, nullable=True)
    invited: Column = Column(BIGINT, nullable=True)

    __table_args__ = (
        ForeignKeyConstraint(['invited'], ['telegram_id']),
        ForeignKeyConstraint(['server_id'], ['servers.id'])
    )


class ServersTable(Base):

    __tablename__: str = 'servers'

    id: Column = Column(INTEGER, primary_key=True)
    links: Column = Column(TEXT, nullable=False)
    country: Column = Column(INTEGER, nullable=False)
    name: Column = Column(TEXT, nullable=False)
    speed: Column = Column(INTEGER)
    answers: Column = Column(BOOLEAN, nullable=False, server_default=text("true"))
    panel_xray: Column = Column(SMALLINT, nullable=False)


class CountryTable(Base):

    __tablename__: str = 'country'

    id: Column = Column(INTEGER, primary_key=True)
    name: Column = Column(TEXT, nullable=False)


class SecurityHashs(Base):

    __tablename__: str = 'securityhashs'

    hash = Column(TEXT, primary_key=True)
    data = Column(TIMESTAMP(timezone=True), nullable=False)


class SaleInvoicesInProgress(Base):
    
    __tablename__: str = 'sale_invoices_in_progress'

    id: Column = Column(BIGINT, primary_key=True)
    telegram_id: Column = Column(BIGINT, nullable=False)
    label: Column = Column(TEXT, nullable=False)
    server_id: Column = Column(BIGINT, nullable=False)
    month_count: Column = Column(SMALLINT, nullable=False)
    message_id: Column = Column(BIGINT, nullable=False)
    chat_id: Column = Column(BIGINT, nullable=False)
    create_date: Column = Column(TIMESTAMP, nullable=False, server_default=func.now())
    is_gift = Column(BOOLEAN, nullable=False, server_default=text("false"))
    gift_recipient_email: Column = Column(TEXT, nullable=True)

    __table_agrs___ = (
        ForeignKeyConstraint(['telegram_id'], ['users_subscription.telegram_id']),
        ForeignKeyConstraint(['server_id'], ['servers.id'])
    )

class UserNew(Base):

    __tablename__: str = 'users'

    id: Column = Column(BIGINT, primary_key=True)
    email: Column = Column(TEXT, nullable=False)
    telegram_id: Column = Column(BIGINT, nullable=True)

    __table_args__ = (
        ForeignKeyConstraint(['telegram_id'], ['users_subscription.telegram_id']),
    )

class MTProxyConfigs(Base):

    __tablename__: str = 'mtproxy_configs'

    id = Column(BIGINT, primary_key=True)
    server_id = Column(BIGINT, nullable=False)
    url = Column(TEXT, nullable=False)

    __table_agrs__ = (
        ForeignKeyConstraint(['server_id'], ['servers.id'])
    )
    
Base.metadata.create_all(engine)