import React from "react";
import { useRef, useState, useEffect } from "react";
import { Rating, Checkbox, ChoiceGroup, IChoiceGroupOption, Panel, PrimaryButton, DefaultButton, Spinner, TextField, SpinButton, Slider } from "@fluentui/react";
import BootstrapTable from 'react-bootstrap-table-next'; 
import {
    DocumentCard,
    DocumentCardActivity,
    DocumentCardDetails,
    DocumentCardPreview,
    DocumentCardTitle,
    IDocumentCardPreviewProps,
    DocumentCardType,
    IDocumentCardActivityPerson,
  } from '@fluentui/react/lib/DocumentCard';

import styles from "./Review.module.css";
import { Stack, IStackTokens } from '@fluentui/react';

import { Answer, AnswerError } from "../../components/Answer";
import { QuestionInput } from "../../components/QuestionInput";
import { ExampleList } from "../../components/Example";
import { AnalysisPanel, AnalysisPanelTabs } from "../../components/AnalysisPanel";

export const Review = ({comment, date, rating, version, tags, topics}) => {
    return (
        <div className={styles.review}>
            <div>{comment}</div>
            <div>
                <Rating 
                    className={styles.rating}
                    max={5}
                    defaultRating={rating}
                    ariaLabel="Rating"
                    ariaLabelFormat="{0} of {1}"
                    readOnly /> 
                <span className={styles.ratingText}>({rating}/5)</span>
                <span className={styles.ratingTag}>{date}</span>
                <span className={styles.ratingTag}>v{version}</span>
            </div>
            {/* <div>Tags: 
                <span className={styles.ratingTag}>{tags}</span>
            </div> */}
            <div>Topics: 
                <span className={styles.ratingTag}>{topics}</span>
            </div>
            
        </div>
    );
};
