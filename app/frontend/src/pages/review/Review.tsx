import React from "react";
import { useRef, useState, useEffect } from "react";
import { Rating, Checkbox, ChoiceGroup, IChoiceGroupOption, Panel, PrimaryButton, DefaultButton, Spinner, TextField, SpinButton, Slider } from "@fluentui/react";
import { useId } from '@fluentui/react-hooks';
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

import "./Review.css";
import { Stack, IStackTokens } from '@fluentui/react';

import { Answer, AnswerError } from "../../components/Answer";
import { QuestionInput } from "../../components/QuestionInput";
import { ExampleList } from "../../components/Example";
import { AnalysisPanel, AnalysisPanelTabs } from "../../components/AnalysisPanel";


interface Props {
    comment: string;
    date: string;
    rating: number;
    version: string;
    tags: string[];
    topics: string[];
}

export const Review = ({comment, date, rating, version, tags, topics}:Props) => {
    let id = useId('review');
    const [tagTypeToShow, setTagTypeToShow] = useState('topics')
    
    return (
        <div className="review">
            <div>{comment}</div>
            <div>
                <Rating 
                    className="rating"
                    max={5}
                    defaultRating={rating}
                    ariaLabel="Rating"
                    ariaLabelFormat="{0} of {1}"
                    readOnly /> 
                <span className="ratingText">({rating}/5)</span>
                <span className="ratingTag">{date}</span>
                <span className="ratingTag">v{version}</span>
            </div>
            {tagTypeToShow == 'topics' && <div><span className="tagType" onClick={() => setTagTypeToShow('tags')}>Topics: </span>
                {topics.map((t, i) => <span key={i} className="ratingTag ratingTagPrimary">{t}</span>)}
            </div>}
            {tagTypeToShow == 'tags' && <div><span className="tagType" onClick={() => setTagTypeToShow('topics')}>Tags: </span>
                {tags.map((t, i) => <span key={i} className="ratingTag ratingTagPrimary">{t}</span>)}
            </div>}
            
        </div>
    );
};
