export interface SampleDataset {
  id: string;
  name: string;
  filename: string;
  rows: number;
  cols: number;
  description: string;
  csvContent: string;
}

export const SAMPLE_DATASETS: SampleDataset[] = [
  {
    id: "titanic",
    name: "Titanic Survival",
    filename: "titanic_passengers.csv",
    rows: 25,
    cols: 10,
    description: "Classification benchmark: passenger demographics & survival status",
    csvContent: `PassengerId,Survived,Pclass,Name,Sex,Age,SibSp,Parch,Fare,Embarked
1,0,3,"Braund, Mr. Owen Harris",male,22,1,0,7.25,S
2,1,1,"Cumings, Mrs. John Bradley",female,38,1,0,71.2833,C
3,1,3,"Heikkinen, Miss. Laina",female,26,0,0,7.925,S
4,1,1,"Futrelle, Mrs. Jacques Heath",female,35,1,0,53.1,S
5,0,3,"Allen, Mr. William Henry",male,35,0,0,8.05,S
6,0,3,"Moran, Mr. James",male,,0,0,8.4583,Q
7,0,1,"McCarthy, Mr. Timothy J",male,54,0,0,51.8625,S
8,0,3,"Palsson, Master. Gosta Leonard",male,2,3,1,21.075,S
9,1,3,"Johnson, Mrs. Oscar W",female,27,0,2,11.1333,S
10,1,2,"Nasser, Mrs. Nicholas",female,14,1,0,30.0708,C
11,1,3,"Sandstrom, Miss. Marguerite Rut",female,4,1,1,16.7,S
12,1,1,"Bonnell, Miss. Elizabeth",female,58,0,0,26.55,S
13,0,3,"Saundercock, Mr. William Henry",male,20,0,0,8.05,S
14,0,3,"Andersson, Mr. Anders Johan",male,39,1,5,31.275,S
15,0,3,"Vestrom, Miss. Hulda Amanda Adolfina",female,14,0,0,7.8542,S
16,1,2,"Hewlett, Mrs.",female,55,0,0,16.0,S
17,0,3,"Rice, Master. Eugene",male,2,4,1,29.125,Q
18,1,2,"Williams, Mr. Charles Eugene",male,,0,0,13.0,S
19,0,3,"Vander Planke, Mrs. Julius",female,31,1,0,18.0,S
20,1,3,"Masselmani, Mrs. Fatima",female,,0,0,7.225,C
21,0,2,"Fynney, Mr. Joseph J",male,35,0,0,26.0,S
22,1,2,"Beesley, Mr. Lawrence",male,34,0,0,13.0,S
23,1,3,"McGowan, Miss. Anna",female,15,0,0,8.0292,Q
24,1,1,"Sloper, Mr. William Thompson",male,28,0,0,35.5,S
25,0,3,"Palsson, Miss. Torborg Danira",female,8,3,1,21.075,S`,
  },
  {
    id: "housing",
    name: "California Housing",
    filename: "california_housing.csv",
    rows: 25,
    cols: 8,
    description: "Regression benchmark: median income, house age & target price",
    csvContent: `MedInc,HouseAge,AveRooms,AveBedrms,Population,AveOccup,Latitude,MedHouseVal
8.3252,41,6.9841,1.0238,322,2.5555,37.88,4.526
8.3014,21,6.2381,0.9718,2401,2.1098,37.86,3.585
7.2574,52,8.2881,1.0734,496,2.8022,37.85,3.521
5.6431,52,5.8173,1.0730,558,2.5479,37.85,3.413
3.8462,52,6.2818,1.0810,565,2.1814,37.85,3.422
4.0368,52,4.7616,1.1036,413,2.1398,37.85,2.697
3.6591,52,4.9319,0.9511,1094,2.3276,37.84,2.992
3.1200,52,4.7975,1.0618,1157,2.4104,37.84,2.414
2.0804,42,4.2941,1.1176,1206,2.0268,37.84,2.267
3.6912,52,4.9705,0.9901,1551,2.1722,37.84,2.611
3.2031,52,5.4776,1.0796,910,2.2636,37.85,2.815
3.2705,52,4.7724,1.0245,1504,2.3499,37.85,2.418
3.0750,52,5.3226,1.0129,1098,2.3612,37.85,2.135
2.6736,52,4.0000,1.0977,1212,1.9868,37.84,1.913
1.9167,52,4.2629,1.0086,1212,2.0896,37.85,1.592
2.1250,50,4.7740,1.0740,697,2.3869,37.85,1.400
2.7750,52,5.9395,1.0205,331,2.3475,37.85,1.525
2.1202,52,4.0528,1.0158,648,1.7097,37.85,1.555
1.9911,50,5.3436,1.1852,990,2.3627,37.84,1.587
2.6033,52,5.4654,1.0660,690,2.1698,37.84,1.629
1.3578,40,4.5240,1.1083,409,1.7404,37.85,1.475
1.7135,42,4.4781,1.0524,929,2.4773,37.85,1.598
1.7250,52,5.0962,1.1314,1015,2.2656,37.84,1.139
2.1806,52,5.1948,1.0346,853,2.4796,37.84,0.997
2.6000,52,5.2701,1.0879,1006,2.2968,37.84,1.326`,
  },
  {
    id: "churn",
    name: "Customer Churn",
    filename: "telecom_customer_churn.csv",
    rows: 25,
    cols: 9,
    description: "SaaS & Telco metrics: contract length, monthly spend & churn risk",
    csvContent: `customerID,gender,SeniorCitizen,tenure,PhoneService,Contract,MonthlyCharges,TotalCharges,Churn
7590-VHVEG,Female,0,1,No,Month-to-month,29.85,29.85,No
5575-GNVDE,Male,0,34,Yes,One year,56.95,1889.5,No
3668-QPYBK,Male,0,2,Yes,Month-to-month,53.85,108.15,Yes
7795-CFOCW,Male,0,45,No,One year,42.3,1840.75,No
9237-HQITU,Female,0,2,Yes,Month-to-month,70.7,151.65,Yes
9305-CDSKC,Female,0,8,Yes,Month-to-month,99.65,820.5,Yes
1452-KIOVK,Male,0,22,Yes,Month-to-month,89.1,1949.4,No
6713-OKOMC,Female,0,10,No,Month-to-month,29.75,301.9,No
7892-POOKP,Female,0,28,Yes,Month-to-month,104.8,3046.05,Yes
6388-TABGU,Male,0,62,No,One year,56.15,3487.95,No
9763-GRSKD,Male,0,13,Yes,Month-to-month,49.95,587.45,No
7469-LKBCI,Male,0,16,Yes,Two year,18.95,326.8,No
8091-TTVAX,Male,0,58,Yes,One year,100.35,5681.1,Yes
0280-XJGEX,Male,0,49,Yes,Month-to-month,103.7,5036.3,Yes
5129-JFDNV,Male,0,25,Yes,Month-to-month,20.65,522.45,No
3655-SNQYZ,Female,0,69,Yes,Two year,113.25,7895.15,No
8191-XWSZG,Female,0,52,Yes,One year,20.65,1022.95,No
9959-WOFSC,Male,0,71,Yes,Two year,52.55,3830.75,No
4183-MYFRB,Female,0,21,Yes,Month-to-month,90.05,1862.9,Yes
8779-QRDMV,Male,1,1,No,Month-to-month,39.65,39.65,Yes
1066-JKSGK,Male,0,1,Yes,Month-to-month,20.15,20.15,Yes
6467-FLFUS,Female,0,12,Yes,Month-to-month,43.75,543.0,No
5492-SEFSR,Male,0,42,Yes,Two year,20.25,865.0,No
1680-VDCWW,Male,0,12,Yes,One year,19.8,202.25,No
6365-MTUVR,Male,0,17,Yes,Month-to-month,55.8,947.65,Yes`,
  },
];
