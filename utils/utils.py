"""
Collection of helper functions
"""
import logging
import argparse
import numpy as np
import psycopg2
import pandas as pd
import sys
import pickle
import plotly.graph_objs as go
from django_pandas.io import read_frame

from scipy import stats
from dateutil.tz import tzutc
from dateutil.parser import parse
from django.utils.timezone import make_aware
from django.conf import settings
from predictor.models import TrainingSession, LendingRate
logger = logging.getLogger(__name__)


# The database parameters
DB_PARAMS = {'host': settings.DATABASES['default']['HOST'],
             'port': settings.DATABASES['default']['PORT'],
             'database': settings.DATABASES['default']['NAME'],
             'user': settings.DATABASES['default']['USER'],
             'password': settings.DATABASES['default']['PASSWORD']
             }


def valid_date(s):
    try:
        return make_aware(parse(s, tzinfos={'UTC': tzutc}))
    except ValueError:
        msg = "Not a valid date: '{0}'.".format(s)
        raise argparse.ArgumentTypeError(msg)


def connect(db_params):
    """ Connect to the PostgreSQL database server """
    conn = None
    try:
        # connect to the PostgreSQL server
        logger.debug('Connecting to the PostgreSQL database...')
        conn = psycopg2.connect(**db_params)
    except (Exception, psycopg2.DatabaseError) as error:
        logger.error(error)
        sys.exit(1)
    logger.debug("Connection successful")
    return conn


def get_forecast_plots(training_session_id, start_date, end_date):

    # Load the Django model corresponding to these options
    try:
        training_session = TrainingSession.objects.get(id=training_session_id)
    except TrainingSession.DoesNotExist as dn_exc:
        logger.error(f'No training session with this id: {training_session_id}')
        return

    qs = training_session.stockprediction_set.all()

    df = read_frame(qs)
    df = df.sort_values(by='dt', ascending=True)

    # Filter date range
    if start_date:
        df = df[df['dt'] >= start_date]
    if end_date:
        df = df[df['dt'] <= end_date]

    graph = []
    for col in ['actual', 'prediction']:
        graph.append(go.Scatter(x=df.dt.tolist(),
                                y=df[col].tolist(),
                                mode='lines',
                                name=col)
                     )

    layout = dict(title=f'Actual vs predicted price over time {training_session.id}',
                  xaxis=dict(title='Date',
                             autotick=True),
                  yaxis=dict(title="Price"),
                  )

    return graph, layout


def get_long_short(predicted_close, current_close):
    """
    Generate the signals long, short

    Parameters
    ----------
    predicted_close : close price predicted at next interval
    current_close: close price now

    Returns
    -------
    long_short : DataFrame
        The long, short, and do nothing signals for each ticker and date
    """
    # If predicted close is greater than the current close then we long
    df1 = (predicted_close >= current_close).astype(int)
    # Otherwise we short if less
    df2 =  -(predicted_close < current_close).astype(int)
    # Combine the 2 (note if no action we'd have False->0 in both)
    return df1 + df2


def get_evaluation_plot(training_session_id, eval_type='train'):

    # Load the Django model corresponding to these options
    try:
        training_session = TrainingSession.objects.get(id=training_session_id)
    except TrainingSession.DoesNotExist as dn_exc:
        logger.error(f'No training session with this id: {training_session_id}')
        return

    qs = training_session.stockprediction_set.all()

    df = read_frame(qs)
    df = df.sort_values(by='dt', ascending=True)

    # Filter date range
    if eval_type == 'train':
        start_date = sorted(training_session.training_dates)[0]
        end_date = sorted(training_session.training_dates)[-1]
    else:
        start_date = sorted(training_session.test_dates)[0]
        end_date = sorted(training_session.test_dates)[-1]
    df = df[df['dt'] >= start_date]
    df = df[df['dt'] <= end_date]

    graph_0 = []
    for col in ['actual', 'prediction']:
        graph_0.append(go.Scatter(x=df.dt.tolist(),
                                y=df[col].tolist(),
                                mode='lines',
                                name=col)
                     )

    layout_0 = dict(title=f'Actual vs predicted price over time ({eval_type} set) {training_session.id}',
                  xaxis=dict(title='Date',
                             autotick=True),
                  yaxis=dict(title="Price"),
                  )

    # Do some profit and significance analysis w/ basic trading strat
    df['actual_shift'] = df['actual'].shift(-1)
    df['prediction_shift'] = df['prediction'].shift(-1)
    df['signal'] = get_long_short(df['prediction_shift'], df['prediction'])
    df['true_signal'] = get_long_short(df['actual_shift'], df['actual'])
    df['return'] = (df['actual_shift'] - df['actual'])/df['actual']
    df['signal_return'] = df['signal'] * df['return']
    df['profit'] = (df['signal_return'].astype(float)+1.0).cumprod()
    df['matches'] = (df['true_signal'] == df['signal']).astype(int)
    mu_null = 0.5
    alpha = 0.05
    pop_mean = df['matches'].mean()
    t, p = stats.ttest_1samp(df['matches'], mu_null)
    # 1 sided
    p = p/2
    logger.debug(f'Got p {p} and t {t}')
    reject_null = False
    if t > 0 and p < alpha:
        # We are looking for greater than 0.5 at level alpha (if t< 0 it means the mean was actually less
        # than 0.5 and no way we reject it the null and claim we are doing better than 50% coin...we may
        # even be doing worse with some signif like 0.4 matches)
        reject_null = True
    graph_1 = [go.Scatter(x=df.dt.tolist(),
                          y=df['profit'].tolist(),
                          mode='lines',
                          name='profit')
               ]

    layout_1 = dict(title=f'Profit over time. Mean: {pop_mean:.2f}, p-value: {p:.2f}, t-score: {t:.2f}.'
                          f'Reject null: {reject_null}',
                    xaxis=dict(title='Date',
                               autotick=True),
                    yaxis=dict(title="% Profit"),
                    )

    return [(graph_0, layout_0), (graph_1, layout_1)]


def get_lending_rates(platform, period, start_date, end_date, fiat_only):

    # Load the Django model corresponding to these options
    lending_rates = LendingRate.objects.filter(platform=platform)
    if fiat_only:
        lending_rates = lending_rates.filter(coin__in=settings.FIAT_CODES)
    # if coin:
    #     lending_rates = lending_rates.filter(coin__in=coin)
    if start_date:
        start_date = parse(start_date) if isinstance(start_date, str) else start_date
        lending_rates = lending_rates.filter(dt__gte=start_date)
    if end_date:
        end_date = parse(end_date) if isinstance(end_date, str) else end_date
        lending_rates = lending_rates.filter(dt__lte=end_date)

    df = read_frame(lending_rates)

    df['term'] = df['term'].fillna('')
    df['coin'] = df['coin'] + df['term'].astype('str')

    df.drop(columns=['id', 'platform', 'previous', 'term'], inplace=True)
    # % hourly
    df['hourly_estimate'] = 100*df['estimate']

    # For now just work with annual est
    if period == 'Annual':
        # % annual
        values_name = 'annual_estimate'
        df[values_name] = df['hourly_estimate'].apply(lambda x: 100*(np.power(1+float(x/100), 24*365)-1))
    elif period == 'Daily':
        # % daily
        values_name = 'daily_estimate'
        df[values_name] = df['hourly_estimate'].apply(lambda x: 100*(np.power(1+float(x/100), 24)-1))
    else:
        values_name = 'hourly_estimate'

    pivot_df = df.pivot(index='dt', columns='coin', values=values_name)
    pivot_df = pivot_df.sort_values(by='dt', ascending=True)

    graph = []
    for coin in pivot_df.columns:
        graph.append(go.Scatter(x=pivot_df.index.tolist(),
                                y=pivot_df[coin].tolist(),
                                mode='lines',
                                name=coin)
                     )

    layout = dict(title=f'Lending rate over time for {platform} (% {period} rate)',
                  xaxis=dict(title='Date',
                             autotick=True),
                  yaxis=dict(title="Lending Rate"),
                  )

    return graph, layout