Methodology for comapring models:

On a spcific day, quarter of hours by quarter of hours between 6am and 10pm, making a prediction of the next 30 minutes values. We calculate then the root mean square error by time slice, then we make the average of the time slice.

Note: the data maybe needs to be divided between day of the week and the weekend.

Note:
For facebook prophet, as it is necessary to have previous values, it is necessary to fit a new model everytime. So running the test if very time consuming: around 19 minutes by stations. Therefore, we will take data every 5 minutes to fasten as much as possible calculation. However, is seems complicated to implement on all velib park without a server.
